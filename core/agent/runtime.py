from pydantic import BaseModel
from typing import Any, Awaitable, Callable

from core.llm import LLM
from core.message import Message
from core.prompts.error import PARSE_LLM_RESPONSE_ERROR, RESULT_HANDLER_ERROR, ACTION_EMPTY_ERROR, ACTION_HANDLER_ERROR
from structure.base_structure import ReAct, AgentPayload, ActionPayload
from utils.logging_setup import configure_logging

logger = configure_logging("RunTime")

ActionHandler = Callable[[str, str], Awaitable[Any]]
ResultHandler = Callable[[str, str], Awaitable[Any]]


class RunTime:
    def __init__(self, max_loops: int = 5):
        self.max_loops = max_loops
        logger.info(f"[Walnut] RunTime initialized with max_loops: {self.max_loops}")

    async def run(
        self,
        message: Message,
        llm: LLM,
        result_handler: ResultHandler,
        action_handler: ActionHandler | None = None,
        caller: str = "WALNUT",
    ) -> BaseModel:
        logger.info(f"[Walnut-{caller}] Starting run with max_loops: {self.max_loops}")
        for i in range(self.max_loops):
            # Get response from the LLM based on the current message context
            response: ReAct = await llm.response_context(message.context)
            message.add_message("assistant", response.model_dump_json())
            if response.error:
                message.add_message("user", PARSE_LLM_RESPONSE_ERROR)
                continue

            logger.info(f"[Walnut-{caller}-loop{i + 1}] Received response from LLM")
            logger.debug(f"[Walnut-{caller}-loop{i + 1}] Response: {response.model_dump_json()}")

            # Handle results from the LLM response
            if response.results:
                result: BaseModel = result_handler(response.results)
                message.add_message("assistant", result.model_dump_json())
                if result.error:  # Any output will include an `error` field.
                    message.add_message("user", RESULT_HANDLER_ERROR)
                    continue

                logger.info(f"[Walnut-{caller}-loop{i + 1}] Get result")
                logger.debug(f"[Walnut-{caller}-loop{i + 1}] Result: {result.model_dump_json()}")
                return result

            # Handle action from the LLM response
            if not response.action:
                message.add_message("user", ACTION_EMPTY_ERROR)
                continue
            action: AgentPayload | ActionPayload = response.action
            observation: BaseModel = await action_handler(action)

            logger.info(f"[Walnut-{caller}-loop{i + 1}] Get observation")
            logger.debug(f"[Walnut-{caller}-loop{i + 1}] Observation: {observation.model_dump_json()}")

            if observation is None:
                message.add_message("user", ACTION_HANDLER_ERROR)
                continue
            if observation.error:
                message.add_message("user", f"Observation error: {observation.error}")
                continue

            message.add_message("user", f"Observation: {observation.model_dump_json()}")

        logger.error(f"[Walnut-{caller}] Run terminated after reaching max loops: {self.max_loops}")
        raise Exception("[任务步数不足]很遗憾未能完成任务!")
