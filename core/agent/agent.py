from abc import abstractmethod
from core.agent.runtime import RunTime
from core.message import Message
from core.tool_manager import ToolManager


class Agent:
    def __init__(self, llm, sub_agent=None):
        self.llm = llm
        self.sub_agent = sub_agent

    @abstractmethod
    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, *args, **kwargs
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def handle_action(self, tool_name: str, raw_arguments: str) -> str:
        raise NotImplementedError
