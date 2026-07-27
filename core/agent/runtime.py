from typing import Any, Awaitable, Callable

from core.llm import LLM
from core.message import Message
from utils.logging_setup import configure_logging

logger = configure_logging("runtime")

ActionHandler = Callable[[str, str], Awaitable[Any]]


class RunTime:
    def __init__(self, max_loops: int = 5):
        self.max_loops = max_loops

    async def run(self, message: Message, llm: LLM, action_handler: ActionHandler) -> tuple[str, int]:
        logger.info(f"Starting runtime loop")

        for i in range(self.max_loops):
            logger.info(f"RunTime loop: {i + 1}")

            response = await llm.response_context(message.context)
            logger.info(f"LLM response: {response}")
            message.add_message("assistant", f"Thought: {response} Action")
            if isinstance(response, str):
                message.add_message("assistant", response)
                message.add_message("user", "请按照规定的格式输出, 以便我能正确解析!")
                continue
            else:
                message.add_message("assistant", f"Thought: {response} Action")

            if response["Results"] is not None:
                return response["Results"], 1

            action = self._parse_action(response)
            if action is None:
                message.add_message("user", "请按照规定的格式输出, 以便我能正确解析!")
                continue

            observation = await action_handler(action)
            if observation is None:
                message.add_message(
                    "user",
                    f"Action执行失败, 请按照以下步骤检查并修正: 1.检查输出格式是否正确 2.请对照工具列表检查工具名称和参数是否正确, 3.Assets的路径是否正确",
                )
                continue

            message.add_message("user", f"Observation: {observation}")

        return "[任务步数不足]很遗憾未能完成任务!", 0  # Return status code 0 for failure

    def _parse_action(self, response: str) -> tuple[str, str] | None:
        if response["Results"] is None and response["Action"] is None:
            return None

        try:
            return response["Action"]
        except ValueError:
            logger.info(f"Failed to parse 'Action' from response: {response}")
            return None
