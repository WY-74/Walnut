import os

from typing import Any
from openai import OpenAI
from pathlib import Path
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack, asynccontextmanager

from prompts.system import SYSTEM_PROMPT, SYSTEM_PROMPT_WITHOUT_TOOLS
from utils.format import MCPServerSpec, SkillServerSpec, ToolSpec
from utils.skill_session import SkillSession


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


class Manager:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {"skill": None}  # 对于Skill部分session不起任何作用, 只需要注册即可
        self.tools: dict[str, ToolSpec] = {}

    @asynccontextmanager
    async def open_mcp_session(self, command: str, args: list[str], env: dict[str, str] | None = None):
        params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {},
        )

        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    @asynccontextmanager
    async def open_skill_session(self, skill_path: str):
        session = SkillSession(skill_path)
        await session.initialize()
        yield session

    async def add_mcp_server(self, spec: MCPServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(self.open_mcp_session(spec.mcp_command, spec.mcp_args, spec.mcp_env))
        self.sessions[spec.mcp_server_name] = session

        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"{spec.mcp_server_name}.{tool.name}"  # mcp_server_name.tool_name
            self.tools[full_name] = ToolSpec(
                server_name=spec.mcp_server_name, tool_name=tool.name, tool_description=tool.description or ""
            )

    async def add_skill_server(self, spec: SkillServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(self.open_skill_session(spec.skill_path))
        self.sessions[spec.skill_name] = session

        full_name = f"skill.{spec.skill_name}"  # skill 没有tools列表, 其skill_name就是tool_name
        self.tools[full_name] = ToolSpec(
            server_name="skill", tool_name=spec.skill_name, tool_description=session.description
        )

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool: ToolSpec = self._resolve_tool(tool_name)
        if tool is None:
            return None

        if tool.server_name == "skill":
            session = self.sessions[tool.tool_name]  # SKILL的session是以tool_name(skill_name)作为key存储的
        else:
            session = self.sessions[tool.server_name]

        result = await session.call_tool(tool.tool_name, arguments)
        return self._format_tool_result(result)

    def list_tools(self, tool_type: str) -> list[ToolSpec]:
        if tool_type == "skill":
            return [self.tools[name] for name in sorted(self.tools) if name.startswith("skill.")]
        else:
            return [self.tools[name] for name in sorted(self.tools) if not name.startswith("skill.")]

    def _resolve_tool(self, tool_name: str) -> ToolSpec:
        if tool_name in self.tools:
            return self.tools[tool_name]
        else:
            return None

    def _format_tool_result(self, result: Any) -> dict[str, Any]:
        content_parts = []
        for item in result.content:
            if getattr(item, "type", None) == "text":
                content_parts.append(item.text)
            else:
                content_parts.append(str(item))

        payload: dict[str, Any] = {"content": content_parts}
        structured = getattr(result, "structuredContent", None)
        if structured is not None:
            payload["structuredContent"] = structured
        payload["isError"] = getattr(result, "isError", False)

        return payload


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
