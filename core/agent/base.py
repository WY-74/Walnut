from typing import Callable, Dict, Any

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.structure import ActionPayload, PlainTextResult
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("BaseAgent")


class BaseAgent:
    description: str = ""

    def __init__(self, llm: LLM, progress_store: SQLiteStore | None = None, **sub_agents):
        self.llm = llm
        self.progress_store = progress_store
        self._init_sub_agents(sub_agents)
        self.node_name: str

    def _init_sub_agents(self, sub_agents: Dict[str, Callable]):
        sub_agents = sub_agents["sub_agent"]
        if not sub_agents:
            logger.warning(f"No sub-agents provided to {self.__class__.__name__}.")
            return

        for key, value in sub_agents.items():
            setattr(self, key, value)

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, *args, **kwargs
    ):
        raise NotImplementedError("Subclasses must implement the run method.")

    async def run_without_runtime(self, query: str, extra: Any, *args, **kwargs):
        """
        Run the agent without a runtime.
        Suitable for single-turn Q&A tasks, avoiding the consumption associated with lengthy prompts.
        The output maintains a structure consistent with the Agent's `parse_result`.
        """
        message = Message()
        query = f"{query}结果以json格式返回\n补充信息:\n{str(extra)}"
        # When response_format is set to json_object, the prompt must contain the word "json" (in any form)

        message.add_message("user", query)
        result: str = await self.llm.response_context(message.context, with_react=False)
        return self.parse_result(result)

    def handle_action(self, *args, **kwargs) -> Callable:
        async def handler(action: ActionPayload):
            raise NotImplementedError("Subclasses must implement the run method.")

        return handler

    def init_message(self, message: Message, tool_manager: ToolManager, *args, **kwargs) -> Message:
        raise NotImplementedError("Subclasses must implement the run method.")

    def parse_result(self, result: str, *args, **kwargs) -> dict:
        return PlainTextResult(result=result, error=None)
