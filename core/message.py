from typing import List

from core.prompts.system import SYSTEM_PROMPT, SKILL_SYSTEM_PROMPT
from utils.format import ToolSpec
from utils.logging_setup import configure_logging

logger = configure_logging("message")


class Message:
    def __init__(self):
        self.context: list[dict[str, str]] = []  # 当前对话记录
        self.history: list[dict[str, str]] = []  # 留存完整对话记录

    def reset_context(self):
        self.context = []

    def init_main_message(self, valid_skills: List[ToolSpec] | None = None) -> None:
        """初始化 MainAgent 对话消息"""
        skills = valid_skills or []
        skill_lines = [f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in skills]

        content = SYSTEM_PROMPT.format('\n'.join(skill_lines))

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

        logger.info(f"Initialized MainAgent message: {content}")

    def init_skill_message(self, valid_mcp_tools: List[ToolSpec] | None = None, skill_detail: str = "") -> None:
        """初始化 SkillAgent 对话消息"""
        tools = valid_mcp_tools or []
        tool_lines = [f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}" for tool in tools]

        content = SKILL_SYSTEM_PROMPT.format('\n'.join(tool_lines), skill_detail)

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

        logger.info(f"Initialized SkillAgent message: {content}")

    def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
        self.history.append({"role": role, "content": content})
