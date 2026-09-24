from typing import Any
from pydantic import BaseModel, Field

__all__ = [
    "MCPServerSpec",
    "SkillServerSpec",
    "ToolSpec",
    "Tool",
    "ActionPayload",
    "AgentPayload",
    "ReAct",
    "PlainTextResult",
]


class MCPServerSpec(BaseModel):
    mcp_server_name: str
    mcp_command: str
    mcp_args: list[str]
    mcp_env: dict[str, str]


class ToolSpec(BaseModel):
    server_name: str
    tool_name: str
    tool_description: str


class SkillServerSpec(BaseModel):
    skill_name: str
    skill_path: str
    skill_description: str = ""
    skill_need_tools: list[str] = Field(default_factory=list)


class Tool(BaseModel):
    target: str
    name: str
    args: dict | None


class ActionPayload(BaseModel):
    assets: list[str] | None
    tool_call: list[Tool] | None


class AgentPayload(BaseModel):
    agent: str
    task: str
    references: list[str] = []


class ReAct(BaseModel):
    thought: str
    action: ActionPayload | AgentPayload | None
    results: Any | None
    error: str | None = None


class PlainTextResult(BaseModel):
    result: str
    error: str | None = None
