from typing import Any, Awaitable, Callable

from json import JSONDecodeError
from pydantic import ValidationError

from core.llm import LLM
from core.message import Message
from core.prompts.error import PARSE_LLM_RESPONSE_ERROR, RESULT_HANDLER_ERROR, ACTION_HANDLER_ERROR
from structure.llm_response import LLMResponse
from utils.logging_setup import configure_logging

logger = configure_logging("runtime")

ActionHandler = Callable[[str, str], Awaitable[Any]]
ResultHandler = Callable[[str, str], Awaitable[Any]]


class RunTime:
    def __init__(self, max_loops: int = 5):
        self.max_loops = max_loops

    async def run(
        self, message: Message, llm: LLM, result_handler: ResultHandler, action_handler: ActionHandler | None = None
    ) -> tuple[str, int]:
        response: LLMResponse
        logger.info(f"Starting runtime loop")

        for i in range(self.max_loops):
            logger.info(f"RunTime loop: {i + 1}")

            response = await llm.response_context(message.context)
            message.add_message("assistant", response.model_dump_json())
            if response.available is False:
                message.add_message("user", PARSE_LLM_RESPONSE_ERROR)
                continue

            if response.results is not None:
                try:
                    result = result_handler(response.results)
                    return result, 1
                except (ValidationError, JSONDecodeError) as e:
                    message.add_message("user", RESULT_HANDLER_ERROR)
                    logger.warning(f"Result handler failed: {e}")
                    continue

            action = response.action if response.action else None
            observation = await action_handler(action)
            if observation is None:
                message.add_message("user", ACTION_HANDLER_ERROR)
                continue

            message.add_message("user", f"Observation: {observation}")

        result = result_handler("[任务步数不足]很遗憾未能完成任务!")
        return result, 0  # Return status code 0 for failure
