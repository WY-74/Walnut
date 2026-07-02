import json
from typing import Any, List, Dict, Callable, Awaitable

from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from contextlib import AsyncExitStack, asynccontextmanager

from utils.format import MCPServerSpec, SkillServerSpec, ToolSpec
from utils.skill_session import SkillSession
from utils.logging_setup import configure_logging

logger = configure_logging("ToolManager")


class ToolManager:
    def __init__(self):
        self.sessions: dict[str, ClientSession] = {"skill": None}  # 对于Skill部分session不起任何作用, 只需要注册即可
        self.tools: dict[str, ToolSpec] = {}

    def load_specs(self, settings: Dict[str, Any]) -> tuple[list[MCPServerSpec], list[SkillServerSpec]]:
        # MCP
        mcp_servers = settings.get("mcpServers", {})
        mcp_servers_specs: list[MCPServerSpec] = []
        for name, cfg in mcp_servers.items():
            mcp_servers_specs.append(
                MCPServerSpec(
                    mcp_server_name=name,
                    mcp_command=cfg["command"],
                    mcp_args=cfg.get("args", []),
                    mcp_env=cfg.get("env", {}),
                )
            )

        # Skill
        skills = settings.get("skills", {})
        skills_specs: list[SkillServerSpec] = []
        for name, cfg in skills.items():
            skills_specs.append(SkillServerSpec(skill_name=name, skill_path=cfg["dir"]))

        logger.info(f"Loaded MCP server specs: {mcp_servers_specs}")
        logger.info(f"Loaded Skills specs: {skills_specs}")

        return mcp_servers_specs, skills_specs

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
    async def open_skill_session(self, skills_specs: List[SkillServerSpec]):
        session = SkillSession(skills_specs)
        await session.initialize()
        yield session

    async def add_mcp_servers(self, spec: MCPServerSpec, stack: AsyncExitStack) -> None:
        session = await stack.enter_async_context(self.open_mcp_session(spec.mcp_command, spec.mcp_args, spec.mcp_env))
        self.sessions[spec.mcp_server_name] = session

        tools = await session.list_tools()
        for tool in tools.tools:
            full_name = f"{spec.mcp_server_name}.{tool.name}"  # mcp_server_name.tool_name
            self.tools[full_name] = ToolSpec(
                server_name=spec.mcp_server_name, tool_name=tool.name, tool_description=tool.description or ""
            )
            logger.info(f"Registered tool: {full_name}")

    async def add_skills(self, skills_specs: list[SkillServerSpec], stack: AsyncExitStack) -> None:
        session: SkillSession = await stack.enter_async_context(self.open_skill_session(skills_specs))
        self.sessions["skill"] = session

        skills = await session.list_tools()
        for skill in skills:
            full_name = f"skill.{skill.skill_name}"
            self.tools[full_name] = ToolSpec(
                server_name="skill", tool_name=skill.skill_name, tool_description=skill.skill_description
            )

        logger.info(f"Registered skill")

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool: ToolSpec = self._resolve_tool(tool_name)
        if tool is None:
            return None

        session = self.sessions[tool.server_name]
        arguments = json.loads(arguments) if arguments else {}

        logger.info(f"Calling {tool_name} with arguments: {arguments}")
        result = await session.call_tool(tool.tool_name, arguments)
        logger.info(f"{tool_name} returned result: {result}")

        return self._format_mcp_tool_result(result)

    async def call_skill(self, skill_name: str):
        pass

    def list_mcp_tools(self) -> list[ToolSpec]:
        return [self.tools[name] for name in sorted(self.tools) if not name.startswith("skill.")]

    def list_skills(self) -> list[ToolSpec]:
        return [self.tools[name] for name in sorted(self.tools) if name.startswith("skill.")]

    def _resolve_tool(self, tool_name: str) -> ToolSpec:
        if tool_name in self.tools:
            return self.tools[tool_name]
        else:
            return None

    def _format_mcp_tool_result(self, result: Any) -> dict[str, Any]:
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
