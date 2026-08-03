from typing import Any, Awaitable, Callable

from core.llm import LLM
from core.message import Message
from core.prompts.error import PARSE_LLM_RESPONSE_ERROR, ACTION_HANDLER_ERROR
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
            message.add_message("assistant", str(response))
            if response.get("Available") is False:
                message.add_message("user", PARSE_LLM_RESPONSE_ERROR)
                continue

            if response["Results"] is not None:
                return response["Results"], 1

            action = self._parse_action(response)
            observation = await action_handler(action)
            if observation is None:
                message.add_message("user", ACTION_HANDLER_ERROR)
                continue

            message.add_message("user", f"Observation: {observation}")

        return "[任务步数不足]很遗憾未能完成任务!", 0  # Return status code 0 for failure

    def _parse_action(self, response: str) -> tuple[str, str] | None:
        if response["Action"] is None:
            return None

        try:
            return response["Action"]
        except ValueError:
            logger.info(f"Failed to parse 'Action' from response: {response}")
            return None
