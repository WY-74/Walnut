from utils.logging_setup import configure_logging

logger = configure_logging("message")


class Message:
    def __init__(self):
        self.context: list[dict[str, str]] = []  # 当前对话记录

    def reset_context(self):
        self.context = []

    def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
