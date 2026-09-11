from dataclasses import dataclass, field
from pydantic import BaseModel


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
    skill_description: str = ""
    skill_need_tools: list[str] = field(default_factory=list)  # mcp_server_name


@dataclass(frozen=True)
class ToolSpec:
    server_name: str
    tool_name: str
    tool_description: str
