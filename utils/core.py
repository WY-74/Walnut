import os
from openai import OpenAI

from client import Manager
from prompts.system import SYSTEM_PROMPT, SYSTEM_PROMPT_WITHOUT_TOOLS


class LLM:
    def __init__(self):
        self.llm = OpenAI(api_key=os.environ.get('DEEPSEEK_API_KEY'), base_url="https://api.deepseek.com")

    def llm_response_context(self, messages):
        response = self.llm.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            stream=False,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )
        return response.choices[0].message.content


class Message:
    def __init__(self, manager: Manager = None):
        self.context = []  # 当前对话记录
        self.history = []  # 留存完整对话记录
        self.manager = manager

    async def init_message(self, manager: Manager):
        """
        初始化对话消息, 将系统提示和Skill工具列表加入到context和history
        """
        self.manager = manager
        self.valid_skills = self.manager.list_tools("skill")
        self.valid_mcp_tools = self.manager.list_tools("mcp")

        _tools = []
        for tool in self.valid_skills:
            _tools.append(f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}")

        content = SYSTEM_PROMPT + f"\n\n可用工具:\n{'\n'.join(_tools)}"

        self.context.append({"role": "system", "content": content})
        self.history.append({"role": "system", "content": content})

    async def downgrade_system_message(self, level: int):
        """
        在高级别未命中的情况下发生降级 (get level 1: mcp->LLM, 2: skill->mcp)
        该操作会重写context, 但不会重置工具调用次数, 也不会重置history
        """
        if level == 2:
            _tools = []
            for tool in self.valid_mcp_tools:
                _tools.append(f"- {tool.server_name}.{tool.tool_name}: {tool.tool_description}")

            content = SYSTEM_PROMPT + f"\n\n可用工具:\n{'\n'.join(_tools)}"

            self.context[0]["content"] = content
            self.history.append({"role": "system", "content": content})

        if level == 1:
            content = SYSTEM_PROMPT_WITHOUT_TOOLS

            self.context[0]["content"] = content
            self.history.append({"role": "system", "content": content})

        return level - 1

    async def add_message(self, role: str, content: str):
        """
        添加对话消息到context和history
        """
        self.context.append({"role": role, "content": content})
        self.history.append({"role": role, "content": content})
