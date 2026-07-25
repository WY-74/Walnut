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
            message.add_message("assistant", response)

            result = self._parse_result(response)
            if result is not None:
                return result, 1  # Return result with status code 1 for success

            action = self._parse_action(response)
            if action is None:
                message.add_message("user", "请按照规定的格式输出, 以便我能正确解析!")
                continue

            tool_name, raw_arguments = action
            observation = await action_handler(tool_name, raw_arguments)
            if observation is None:
                message.add_message("user", f"工具 '{tool_name}' 执行失败, 请对照工具列表检查工具名称和参数是否正确!")
                continue

            message.add_message("user", f"Observation: {observation}")

        return "[任务步数不足]很遗憾未能完成任务!", 0  # Return status code 0 for failure

    def _parse_result(self, response: str) -> str | None:
        if "Results:" not in response:
            return None
        return response.split('Results:', 1)[1].strip()

    def _parse_action(self, response: str) -> tuple[str, str] | None:
        if "Action:" not in response:
            return None

        try:
            tool_name, raw_arguments = response.split("Action:", 1)[1].split("|", 1)
            return tool_name.strip(), raw_arguments.strip()
        except ValueError:
            logger.info(f"Failed to parse action from response: {response}")
            return None

    async def run_without_tools(self, message, llm: LLM):
        while True:
            network = input("未命中任何工具, 是否使用网络查讯作为参考? (y/n): ")
            if network.lower() == "y":
                return await llm.response_context(message)
