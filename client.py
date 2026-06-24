from typing import Any
from pathlib import Path
from dataclasses import dataclass
from contextlib import asynccontextmanager, AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.logging_setup import configure_logging

logger = configure_logging("client")


@dataclass(frozen=True)
class MCPServerSpec:
    mcp_server_name: str
    mcp_command: str
    mcp_args: list[str]
    mcp_env: dict[str, str]


@dataclass(frozen=True)
class SkillServerSpec:
    skill_name: str
    skill_path: str


@dataclass(frozen=True)
class ToolSpec:
    server_name: str
    tool_name: str
    tool_description: str


def _format_tool_result(result: Any) -> dict[str, Any]:
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


def load_mcp_server_specs(settings: dict) -> list[MCPServerSpec]:
    servers = settings.get("mcpServers", {})

    specs: list[MCPServerSpec] = []
    for name, cfg in servers.items():
        specs.append(
            MCPServerSpec(
                mcp_server_name=name,
                mcp_command=cfg["command"],
                mcp_args=cfg.get("args", []),
                mcp_env=cfg.get("env", {}),
            )
        )

    return specs


def load_skill_server_specs(settings: dict) -> list[SkillServerSpec]:
    skills = settings.get("skills", {})

    specs: list[SkillServerSpec] = []
    for name, cfg in skills.items():
        specs.append(SkillServerSpec(skill_name=name, skill_path=cfg["dir"]))

    return specs


@asynccontextmanager
async def open_manager(settings: dict):
    manager = Manager()

    mcp_server_specs = load_mcp_server_specs(settings)
    skill_server_specs = load_skill_server_specs(settings)

    # 对于Skill部分session不起任何作用, 只需要注册即可
    if skill_server_specs:
        manager.sessions["skill"] = None

    async with AsyncExitStack() as stack:
        for spec in mcp_server_specs:
            await manager.add_mcp_server(spec, stack)
        for spec in skill_server_specs:
            manager.add_skill_server(spec)
        yield manager


@asynccontextmanager
async def open_mcp_session(command: str, args: list[str], env: dict[str, str] | None = None):
    params = StdioServerParameters(
        command=command,
        args=args,
        env=env or {},
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


class Manager:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, ToolSpec] = {}

    async def add_mcp_server(self, spec: MCPServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(open_mcp_session(spec.mcp_command, spec.mcp_args, spec.mcp_env))
        self.sessions[spec.mcp_server_name] = session

        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"{spec.mcp_server_name}.{tool.name}"  # session_name.tool_name
            self.tools[full_name] = ToolSpec(
                server_name=spec.mcp_server_name, tool_name=tool.name, tool_description=tool.description or ""
            )

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.resolve_tool(tool_name)
        if tool is None:
            return None

        session = self.sessions[tool.server]
        result = await session.call_tool(tool.name, arguments)

        return _format_tool_result(result)

    def add_skill_server(self, spec: SkillServerSpec) -> None:
        # 强制以skill作为server_name, setting.json中得到的skill_name作为tool_name
        # 因此SKILL.md中的name将不被使用
        full_name = f"skill.{spec.skill_name}"  # session_name.tool_name
        description = self.resolve_skill_description(spec.skill_path)
        self.tools[full_name] = ToolSpec(server_name="skill", tool_name=spec.skill_name, tool_description=description)

    def list_tools(self) -> list[ToolSpec]:
        return [self.tools[name] for name in sorted(self.tools)]

    def resolve_tool(self, tool_name: str) -> ToolSpec:
        if tool_name in self.tools:
            return self.tools[tool_name]
        else:
            return None

    def resolve_skill_description(self, skill_path: str) -> str:
        with open(Path(skill_path) / "SKILL.md", "r", encoding="utf-8") as f:
            lines = f.readlines()

        return lines[2].strip() if len(lines) > 2 else ""
