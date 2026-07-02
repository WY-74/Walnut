from typing import List

from utils.logging_setup import configure_logging
from utils.format import ToolSpec

logger = configure_logging("message")


class Message:
    def __init__(self):
        self.context = []  # 当前对话记录
        self.history = []  # 留存完整对话记录

    async def init_message(
        self, system_prompt: str, valid_skills: List[ToolSpec] = [], valid_mcp_tools: List[ToolSpec] = []
    ):
        """初始化对话消息"""
        if valid_skills:
            valid_skills = [
                f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in valid_skills
            ]

        if valid_mcp_tools:
            valid_mcp_tools = [
                f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}" for tool in valid_mcp_tools
            ]

        content = system_prompt.format('\n'.join(valid_skills), '\n'.join(valid_mcp_tools))

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

        logger.info(f"Initialized message: {content}")

    async def init_skill_message(
        self, system_prompt: str, valid_mcp_tools: List[ToolSpec] = [], skill_detail: str = ""
    ):
        if valid_mcp_tools:
            valid_mcp_tools = [
                f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}" for tool in valid_mcp_tools
            ]

        content = system_prompt.format('\n'.join(valid_mcp_tools), skill_detail)

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

        logger.info(f"Initialized Skills message: {content}")

    async def downgrade_system_message(self, tools: list[ToolSpec], system_prompt: str):
        """
        该操作会重写context, 但不会重置工具调用次数, 也不会重置history
        """
        if tools:
            valid_tools = []
            for tool in tools:
                valid_tools.append(f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}")

            content = system_prompt + f"\n\n可用工具:\n{'\n'.join(valid_tools)}"
        else:
            content = system_prompt

        self.context[0]["content"] = content
        self.history.append({"role": "system", "content": content})

        logger.info(f"Current message context: {content}")

    async def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
        self.history.append({"role": role, "content": content})
