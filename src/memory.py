from datetime import datetime


class ConversationMemory:
    """
    Gere l'historique de conversation pour que Claude
    ait le contexte des echanges precedents.
    """

    def __init__(self, max_turns: int = 10):
        self.messages = []
        self.last_result = None  # dernier resultat pour l'export
        self.max_turns = max_turns

    def add_user_message(self, content: str):
        self.messages.append({
            "role": "user",
            "content": content
        })
        self._trim()

    def add_assistant_message(self, content: str):
        self.messages.append({
            "role": "assistant",
            "content": content
        })

    def set_last_result(self, data: list, columns: list):
        """Stocke le dernier resultat pour export eventuel."""
        self.last_result = {"data": data, "columns": columns}

    def get_messages(self) -> list:
        return self.messages

    def _trim(self):
        """Garde uniquement les max_turns derniers echanges."""
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-(self.max_turns * 2):]

    def clear(self):
        self.messages = []
        self.last_result = None

    def is_empty(self) -> bool:
        return len(self.messages) == 0