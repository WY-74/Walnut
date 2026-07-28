from typing import List

from core.prompts.system import SYSTEM_PROMPT, SKILL_SYSTEM_PROMPT
from utils.format import ToolSpec
from utils.logging_setup import configure_logging

logger = configure_logging("message")


LLM_RESPONSE_JSON_ERROR = "当前输出无法正常按照json解析, 检查json格式后重新输出!"
PARSE_ACTION_ERROR = "无法正常解析Action, 请按照以下步骤检查后重新输出: 1. 不可能存在Results和Action同时为None的情况, 2. 检查Action是否为标准json格式."
ACTION_HANDLER_ERROR = """Action执行失败, 请按照以下步骤检查并修正: 
1.如果ToolCall不为null则需要确保其格式正确, 之后请对照工具列表检查工具名称和参数是否正确.
2.如果Assets不为null则需要确保其格式正确, 之后确保路径正确. 
3.不可能出现ToolCall和Assets同时为null的情况.
如果上述步骤未发现错误, 则无需多余尝试, 输出并在Results中告知用户执行错误."""


class Message:
    def __init__(self):
        self.context: list[dict[str, str]] = []  # 当前对话记录

    def reset_context(self):
        self.context = []

    def init_main_message(self, tools: List[ToolSpec] | None = None) -> None:
        """初始化 MainAgent 对话消息"""
        skills = tools or []
        skill_lines = [f"- {skill.server_name}.{skill.tool_name}: {skill.tool_description}" for skill in skills]

        content = SYSTEM_PROMPT.format('\n'.join(skill_lines))

        self.context.append({"role": "system", "content": content})
        logger.info(f"Initialized MainAgent message: {content}")

    def init_skill_message(self, tools: List[ToolSpec] | None = None, skill_detail: str = "") -> None:
        """初始化 SkillAgent 对话消息"""
        mcp_tools = tools or []
        tool_lines = [f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}" for tool in mcp_tools]

        content = SKILL_SYSTEM_PROMPT.format('\n'.join(tool_lines), skill_detail)

        self.context.append({"role": "system", "content": content})

        logger.info(f"Initialized SkillAgent message: {content}")

    def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
