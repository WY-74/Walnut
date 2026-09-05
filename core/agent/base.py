from typing import Callable, Dict

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from structure.llm_response import ActionPayload
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("BaseAgent")


class BaseAgent:
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

    def handle_action(self, *args, **kwargs) -> Callable:
        async def handler(action: ActionPayload):
            raise NotImplementedError("Subclasses must implement the run method.")

        return handler

    def init_message(self, message: Message, tool_manager: ToolManager, *args, **kwargs) -> Message:
        raise NotImplementedError("Subclasses must implement the run method.")

    def parse_result(self, result: str | dict, *args, **kwargs) -> dict:
        return result
