from typing import Callable
from pathlib import Path

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("SkillAgent")


class ToolCallAgent:
    def __init__(self, llm: LLM, sub_agent: Callable = None, progress_store: SQLiteStore | None = None):
        self.llm = llm
        self.sub_agent = sub_agent
        self.progress_store = progress_store
        self.node_name = "toolcall"

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, skill_name: str
    ) -> str:
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        skill = tool_manager.get_skill(skill_name)
        if skill is None:
            result = f"Skill '{skill_name}' not found"
            self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=result, status_code=0)
            logger.info(result)
            return None

        skill_detail = tool_manager.get_skill_detail(skill_name)
        if skill_detail is None:
            result = f"Skill detail for {skill_name} is None"
            self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=result, status_code=0)
            logger.info(result)
            return None

        available_tools = tool_manager.list_mcp_tools_for_skill(skill_name)
        if available_tools is None:
            result = f"Available tools for skill {skill_name} is None"
            self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=result, status_code=0)
            logger.info(result)
            return None

        message.reset_context()
        message.init_skill_message(available_tools, skill_detail)
        message.add_message("user", query)

        async def handle_action(action: dict):
            try:
                if action.get("Assets"):
                    assets = self._parse_assets(Path(skill.skill_path), action["Assets"])
                    return assets
                else:
                    tool_name, raw_arguments = action["ToolCall"].split("|", 1)
                    return await tool_manager.call_mcp_tool(tool_name.strip(), raw_arguments.strip())
            except KeyError:
                logger.info(f"Action does not contain 'Assets' key: {action}")
                return None

        result, status_code = await runner.run(message, self.llm, handle_action)
        self.progress_store.finish_node(
            run_id=run_id, node=self.node_name, final_context=result, status_code=status_code
        )
        return result, status_code

    def _parse_assets(self, root: Path, assets: list[str]) -> str:
        result = ""
        try:
            for asset in assets:
                with open(root / asset, "r", encoding="utf-8") as f:
                    content = f.read()
                result += f"[Asset: {asset}]\n{content}\n"
        except Exception as e:
            logger.error(f"Failed to read asset {asset}: {e}")
            return None
        return result
