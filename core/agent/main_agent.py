from asyncio.log import logger
from typing import Callable

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from utils.sqlite_store import SQLiteStore


class MainAgent:
    def __init__(self, llm: LLM, sub_agent: Callable = None, progress_store: SQLiteStore | None = None):
        self.llm = llm
        self.sub_agent = sub_agent
        self.progress_store = progress_store
        self.node_name = "main"

    async def run(self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str) -> str:
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        if not message.context:
            message.init_main_message(tools=tool_manager.list_skills())
        message.add_message("user", query)

        async def handle_action(action: dict):
            try:
                tool_name, raw_arguments = action["ToolCall"].split("|", 1)
            except Exception as e:
                return None

            if not tool_name.startswith("skill."):
                return None

            skill_name = tool_name.split(".", 1)[1].strip()
            skill_message = Message()
            skill_query = self._build_skill_prompt(query, raw_arguments)

            return await self.sub_agent.run(
                query=skill_query,
                runner=runner,
                message=skill_message,
                tool_manager=tool_manager,
                run_id=run_id,
                skill_name=skill_name,
            )

        result, status_code = await runner.run(message=message, llm=self.llm, action_handler=handle_action)
        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result, status_code=status_code
        )
        return result

    def _build_skill_prompt(self, query, raw_arguments: str) -> str:
        if raw_arguments:
            return f"用户原始问题: {query}\n\n当前已知信息: {raw_arguments}"
        else:
            return query
