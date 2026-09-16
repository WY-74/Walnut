import asyncio
from typing import Any, Awaitable, Callable

from json import JSONDecodeError
from pydantic import ValidationError

from core.llm import LLM
from core.message import Message
from core.prompts.error import PARSE_LLM_RESPONSE_ERROR, RESULT_HANDLER_ERROR, ACTION_EMPTY_ERROR, ACTION_HANDLER_ERROR
from structure.base_structure import ReAct
from utils.logging_setup import configure_logging
from utils.tui import RuntimeWindow

logger = configure_logging("RunTime")

ActionHandler = Callable[[str, str], Awaitable[Any]]
ResultHandler = Callable[[str, str], Awaitable[Any]]


class RunTime:
    def __init__(self, max_loops: int = 5):
        self.max_loops = max_loops
        logger.info(f"[Walnut]RunTime initialized with max_loops: {self.max_loops}")

    async def run(
        self,
        message: Message,
        llm: LLM,
        result_handler: ResultHandler,
        action_handler: ActionHandler | None = None,
        caller: str = "WALNUT",
    ) -> tuple[str, int]:
        runtime_window = RuntimeWindow(caller=caller)
        runtime_window.start()

        for i in range(self.max_loops):
            # logger.info(f"RunTime loop: {i + 1}")
            runtime_window.write(f"Loop {i + 1}/{self.max_loops}")

            # Get response from the LLM based on the current message context
            try:
                response: ReAct
                response = await llm.response_context(message.context)
                message.add_message("assistant", response.model_dump_json())
                if response.error:
                    message.add_message("user", PARSE_LLM_RESPONSE_ERROR)
                    continue
            except Exception as e:
                runtime_window.stop()
                raise e

            # Handle results from the LLM response
            if response.results:
                try:
                    result = result_handler(response.results)  # Pydantic object
                    message.add_message("assistant", result.model_dump_json())
                    if result.error:  # Any output will include an `error` field.
                        message.add_message("user", RESULT_HANDLER_ERROR)
                        continue
                    runtime_window.write(result.model_dump_json())
                    return result
                except Exception as e:
                    raise e
                finally:
                    runtime_window.stop()

            # Handle action from the LLM response
            try:
                if not response.action:
                    message.add_message("user", ACTION_EMPTY_ERROR)
                    continue
                action = response.action
                observation = await action_handler(action)
                if observation is None:
                    message.add_message("user", ACTION_HANDLER_ERROR)
                    continue
                runtime_window.write(f"Observation: {observation}")
            except Exception as e:
                runtime_window.stop()
                raise e

            message.add_message("user", f"Observation: {observation}")

        raise Exception("[任务步数不足]很遗憾未能完成任务!")
