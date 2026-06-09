from typing import Any
from dataclasses import dataclass
from contextlib import asynccontextmanager, AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.logging_setup import configure_logging

logger = configure_logging("client")


@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    command: str
    args: list[str]
    env: dict[str, str]


@dataclass(frozen=True)
class ToolSpec:
    server: str
    name: str
    description: str


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


def load_mcp_server_specs(mcp_settings: dict) -> list[MCPServerSpec]:
    servers = mcp_settings.get("mcpServers", {})

    specs: list[MCPServerSpec] = []
    for name, cfg in servers.items():
        specs.append(MCPServerSpec(name=name, command=cfg["command"], args=cfg.get("args", []), env=cfg.get("env", {})))

    return specs


@asynccontextmanager
async def open_mcp_manager(mcp_settings: dict):
    specs = load_mcp_server_specs(mcp_settings)
    manager = MCPManager()

    async with AsyncExitStack() as stack:
        for spec in specs:
            await manager.add_server(spec, stack)
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


class MCPManager:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, ToolSpec] = {}

    async def add_server(self, spec: MCPServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(open_mcp_session(spec.command, spec.args, spec.env))
        self.sessions[spec.name] = session

        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"{spec.name}.{tool.name}"
            self.tools[full_name] = ToolSpec(server=spec.name, name=tool.name, description=tool.description or "")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.resolve_tool(tool_name)
        if tool is None:
            return None

        session = self.sessions[tool.server]
        result = await session.call_tool(tool.name, arguments)

        return _format_tool_result(result)

    def list_tools(self) -> list[ToolSpec]:
        return [self.tools[name] for name in sorted(self.tools)]

    def resolve_tool(self, tool_name: str) -> ToolSpec:
        if tool_name in self.tools:
            return self.tools[tool_name]
        else:
            return None
