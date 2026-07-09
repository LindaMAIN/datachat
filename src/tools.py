import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import traceback


# ─── OUTIL 1 : QUERY DATA ─────────────────────────────────────────────────────
def query_data(df: pd.DataFrame, code: str) -> dict:
    """
    Execute du code pandas genere par Claude sur le dataset.
    Retourne le resultat sous forme de dict serialisable.
    """
    try:
        # Environnement d'execution securise
        local_env = {"df": df.copy(), "pd": pd}
        exec(code, {}, local_env)

        result = local_env.get("result", None)

        if result is None:
            return {"success": False, "error": "Le code n'a pas defini de variable 'result'"}

        if isinstance(result, pd.DataFrame):
            return {
                "success": True,
                "type": "dataframe",
                "data": result.to_dict(orient="records"),
                "columns": result.columns.tolist(),
                "nb_rows": len(result)
            }
        elif isinstance(result, pd.Series):
            return {
                "success": True,
                "type": "series",
                "data": result.reset_index().to_dict(orient="records"),
                "columns": [result.index.name or "index", result.name or "value"],
                "nb_rows": len(result)
            }
        else:
            return {
                "success": True,
                "type": "scalar",
                "data": str(result)
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ─── OUTIL 2 : PLOT CHART ─────────────────────────────────────────────────────
def plot_chart(df: pd.DataFrame, chart_type: str, code: str) -> dict:
    """
    Genere un graphique Plotly a partir de code genere par Claude.
    chart_type : 'bar', 'line', 'pie', 'scatter', 'treemap'
    """
    try:
        local_env = {
            "df": df.copy(),
            "pd": pd,
            "px": px,
            "go": go
        }
        exec(code, {}, local_env)
        fig = local_env.get("fig", None)

        if fig is None:
            return {"success": False, "error": "Le code n'a pas defini de variable 'fig'"}

        return {
            "success": True,
            "type": "chart",
            "fig": fig
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ─── OUTIL 3 : GET SCHEMA ─────────────────────────────────────────────────────
def get_schema_tool(schema_text: str) -> dict:
    """
    Retourne le schema du dataset en reponse directe.
    Utilise quand l'utilisateur pose des questions sur la structure des donnees.
    """
    return {
        "success": True,
        "type": "schema",
        "data": schema_text
    }


# ─── OUTIL 4 : COMPARE PERIODS ────────────────────────────────────────────────
def compare_periods(df: pd.DataFrame, code: str) -> dict:
    """
    Compare des periodes ou des segments.
    Meme logique que query_data mais semantiquement distinct
    pour que Claude choisisse le bon outil.
    """
    return query_data(df, code)


# ─── OUTIL 5 : EXPORT RESULTS ─────────────────────────────────────────────────
def export_results(data: list, columns: list, format: str = "csv") -> dict:
    """
    Genere un fichier CSV ou Excel exportable depuis les resultats.
    """
    try:
        result_df = pd.DataFrame(data, columns=columns)

        if format == "csv":
            output = result_df.to_csv(index=False).encode('utf-8')
            return {
                "success": True,
                "type": "export",
                "format": "csv",
                "data": output,
                "filename": "datachat_export.csv"
            }
        else:
            buffer = io.BytesIO()
            result_df.to_excel(buffer, index=False)
            return {
                "success": True,
                "type": "export",
                "format": "xlsx",
                "data": buffer.getvalue(),
                "filename": "datachat_export.xlsx"
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── DEFINITIONS DES OUTILS POUR CLAUDE ───────────────────────────────────────
TOOLS_DEFINITION = [
    {
        "name": "query_data",
        "description": (
            "Execute une analyse sur le dataset Superstore. "
            "Utilise cet outil pour repondre a des questions quantitatives : "
            "top produits, ventes par region, profit par categorie, moyennes, etc. "
            "Le code doit stocker le resultat dans une variable nommee 'result'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code pandas valide. Utilise 'df' comme nom du DataFrame. Stocke le resultat dans 'result'."
                },
                "explanation": {
                    "type": "string",
                    "description": "Explication en francais de ce que le code fait et pourquoi."
                }
            },
            "required": ["code", "explanation"]
        }
    },
    {
        "name": "plot_chart",
        "description": (
            "Genere un graphique Plotly pour visualiser les donnees. "
            "Utilise cet outil quand l'utilisateur demande un graphique, une visualisation, "
            "ou quand une reponse visuelle serait plus claire qu'un tableau. "
            "Le code doit stocker le graphique dans une variable nommee 'fig'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie", "scatter", "treemap"],
                    "description": "Type de graphique"
                },
                "code": {
                    "type": "string",
                    "description": "Code Plotly valide. Utilise 'df', 'px' et 'go'. Stocke le graphique dans 'fig'."
                },
                "explanation": {
                    "type": "string",
                    "description": "Ce que le graphique montre."
                }
            },
            "required": ["chart_type", "code", "explanation"]
        }
    },
    {
        "name": "get_schema",
        "description": (
            "Retourne la structure et les colonnes disponibles du dataset. "
            "Utilise cet outil quand l'utilisateur demande quelles donnees sont disponibles, "
            "quelles colonnes existent, ou comment le dataset est structure."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Pourquoi tu as besoin du schema."
                }
            },
            "required": ["reason"]
        }
    },
    {
        "name": "compare_periods",
        "description": (
            "Compare des periodes de temps ou des segments entre eux. "
            "Utilise cet outil pour des questions du type : "
            "'compare 2016 et 2017', 'evolution des ventes', 'croissance par trimestre'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Code pandas pour la comparaison. Stocke le resultat dans 'result'."
                },
                "explanation": {
                    "type": "string",
                    "description": "Ce que la comparaison montre."
                }
            },
            "required": ["code", "explanation"]
        }
    },
    {
        "name": "export_results",
        "description": (
            "Exporte les derniers resultats en CSV ou Excel. "
            "Utilise cet outil quand l'utilisateur demande a telecharger ou exporter les donnees."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["csv", "xlsx"],
                    "description": "Format d'export"
                }
            },
            "required": ["format"]
        }
    }
]