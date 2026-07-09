import anthropic
import os
import streamlit as st
from dotenv import load_dotenv

from src.data_loader import schema_to_prompt
from src.tools import (
    query_data, plot_chart, get_schema_tool,
    compare_periods, export_results, TOOLS_DEFINITION
)
from src.memory import ConversationMemory


def get_api_key() -> str:
    try:
        key = st.secrets["ANTHROPIC_API_KEY"]
        if key:
            return key
    except Exception as e:
        pass
    
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY")
    return key


SYSTEM_PROMPT = """Tu es DataChat, un agent analytique expert en données business.
Tu aides les utilisateurs à analyser un dataset de ventes en répondant à leurs questions en français.

{schema}

REGLES IMPORTANTES :
- Utilise TOUJOURS un outil pour répondre aux questions sur les données. Ne devine jamais les chiffres.
- Quand tu génères du code pandas, stocke TOUJOURS le résultat dans une variable nommée 'result'.
- Quand tu génères un graphique Plotly, stocke TOUJOURS le graphique dans une variable nommée 'fig'.
- Après avoir utilisé un outil, explique le résultat en langage naturel clair et concis.
- Cite toujours la source : "Source : Superstore Sales Dataset, {nb_rows} transactions"
- Si une question est ambiguë, pose une question de clarification avant d'utiliser un outil.
- Pour les comparaisons temporelles, utilise df['Order Date'].dt.year pour filtrer par année.
"""


class DataChatAgent:

    def __init__(self, df, schema: dict):
        self.df = df
        self.schema = schema
        self.memory = ConversationMemory(max_turns=10)
        self.client = anthropic.Anthropic(api_key=get_api_key())
        schema_text = schema_to_prompt(schema)
        self.system_prompt = SYSTEM_PROMPT.format(
            schema=schema_text,
            nb_rows=schema['nb_rows']
        )
        api_key = get_api_key()
        if not api_key:
            st.error("Clé API non trouvée. Vérifiez les secrets Streamlit.")
            st.stop()
        self.client = anthropic.Anthropic(api_key=api_key)

    def chat(self, user_message: str) -> dict:
        self.memory.add_user_message(user_message)
        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=self.system_prompt,
            tools=TOOLS_DEFINITION,
            messages=self.memory.get_messages()
        )
        return self._process_response(response)

    def _process_response(self, response) -> dict:
        result = {
            "text": "",
            "chart": None,
            "table": None,
            "export": None,
            "tool_used": None
        }

        while response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    result["tool_used"] = tool_name
                    tool_result = self._execute_tool(tool_name, tool_input, result)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result)
                    })

            self.memory.messages.append({
                "role": "assistant",
                "content": response.content
            })
            self.memory.messages.append({
                "role": "user",
                "content": tool_results
            })

            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=self.system_prompt,
                tools=TOOLS_DEFINITION,
                messages=self.memory.get_messages()
            )

        for block in response.content:
            if hasattr(block, "text"):
                result["text"] = block.text
                break

        self.memory.add_assistant_message(result["text"])
        return result

    def _execute_tool(self, tool_name: str, tool_input: dict, result: dict) -> str:
        if tool_name == "query_data":
            tool_result = query_data(self.df, tool_input["code"])
            if tool_result["success"] and tool_result["type"] in ["dataframe", "series"]:
                result["table"] = tool_result
                self.memory.set_last_result(
                    tool_result["data"],
                    tool_result["columns"]
                )
            return str(tool_result)

        elif tool_name == "plot_chart":
            tool_result = plot_chart(self.df, tool_input["chart_type"], tool_input["code"])
            if tool_result["success"]:
                result["chart"] = tool_result["fig"]
            return str({"success": tool_result["success"], "chart_type": tool_input["chart_type"]})

        elif tool_name == "get_schema":
            schema_text = schema_to_prompt(self.schema)
            tool_result = get_schema_tool(schema_text)
            return tool_result["data"]

        elif tool_name == "compare_periods":
            tool_result = compare_periods(self.df, tool_input["code"])
            if tool_result["success"] and tool_result["type"] in ["dataframe", "series"]:
                result["table"] = tool_result
                self.memory.set_last_result(
                    tool_result["data"],
                    tool_result["columns"]
                )
            return str(tool_result)

        elif tool_name == "export_results":
            if self.memory.last_result:
                tool_result = export_results(
                    self.memory.last_result["data"],
                    self.memory.last_result["columns"],
                    tool_input.get("format", "csv")
                )
                result["export"] = tool_result
            return str({"success": True, "format": tool_input.get("format", "csv")})

        return str({"success": False, "error": f"Outil inconnu : {tool_name}"})

    def reset(self):
        self.memory.clear()
