from core.llm import LLM
from core.message import Message
from core.tool_manager import ToolManager
from core.agent.runtime import RunTime
from utils.logging_setup import configure_logging

logger = configure_logging("SkillAgent")


class SkillAgent:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def run(
        self, query: str, runner: RunTime, message: Message, tool_manager: ToolManager, skill_name: str, *args, **kwargs
    ) -> str:
        skill = tool_manager.get_skill(skill_name)
        if skill is None:
            logger.info(f"Skill {skill_name} is None")
            return None

        skill_detail = tool_manager.get_skill_detail(skill_name)
        if skill_detail is None:
            logger.info(f"Skill detail for {skill_name} is None")
            return None

        available_tools = tool_manager.list_mcp_tools_for_skill(skill_name)
        if available_tools is None:
            logger.info(f"Available tools for skill {skill_name} is None")
            return None

        message.reset_context()
        message.init_skill_message(available_tools, skill_detail)
        message.add_message("user", query)

        async def handle_action(tool_name: str, raw_arguments: str, extra: str | None = None):
            return await tool_manager.call_mcp_tool(tool_name, raw_arguments)

        return await runner.run(message, self.llm, handle_action)
