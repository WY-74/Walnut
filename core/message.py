import json
from typing import Any

from utils.logging_setup import configure_logging

logger = configure_logging("Message")


class Message:
    def __init__(self):
        self.context: list[dict[str, str]] = []  # 当前对话记录
        logger.info("[Walnut] Message initialized.")

    def reset_context(self):
        self.context = []

    def add_message(self, role: str, content: Any):
        """
        添加对话消息到context和history
        """
        if not isinstance(content, str):
            content = json.dumps(content)  # The chat.completions must be a Dict(str, str) as messages

        message = {"role": role, "content": content}
        self.context.append(message)

    def clear_plan(self):
        for idx in range(len(self.context) - 1, -1, -1):
            if self.context[idx].get("type") == "plan":
                del self.context[idx]
                return
