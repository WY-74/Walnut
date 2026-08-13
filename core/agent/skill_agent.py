from typing import Callable
from pathlib import Path

from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from core.prompts.skill_prompt import SKILL_SYSTEM_PROMPT
from utils.sqlite_store import SQLiteStore
from utils.logging_setup import configure_logging

logger = configure_logging("SkillAgent")


class SkillAgent:
    def __init__(self, llm: LLM, sub_agent: Callable = None, progress_store: SQLiteStore | None = None):
        self.llm = llm
        self.sub_agent = sub_agent
        self.progress_store = progress_store
        self.node_name = "pe_ttm"

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, run_id: str, skill_name: str
    ) -> str:
        self.progress_store.start_node(run_id=run_id, node=self.node_name)

        skill = tool_manager.get_skill(skill_name)
        if skill is None:
            result = f"Skill '{skill_name}' not found"
            self.progress_store.finish_node(run_id=run_id, node=self.node_name, final_context=result, status_code=0)
            logger.info(result)
            return None, 0

        message = self.init_message(message=message, tool_manager=tool_manager, skill_name=skill_name)
        message.add_message("user", query)

        # TODO: 完成handle_action
        # TODO: 统一Agent返回为 result(规范处理, 结构化输出, 想办法让结果可以通过属性调用方式使用，纯字典有点麻烦), status_code
        # TODO: 异常处理(例如skill找不到)

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
        return result

    def init_message(self, message: Message, tool_manager: ToolManager, skill_name: str) -> Message:
        message.reset_context()

        tools = [
            f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}"
            for tool in tool_manager.list_mcp_tools_for_skill(skill_name)
        ]
        detail = tool_manager.get_skill_detail(skill_name)

        system_prompt = SKILL_SYSTEM_PROMPT.format(tools='\n'.join(tools), detail=detail)

        message.reset_context()
        message.context.append({"role": "system", "content": system_prompt})
        return message

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
