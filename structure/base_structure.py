from typing import Any
from pydantic import BaseModel


class Tool(BaseModel):
    target: str
    name: str
    args: dict | None


class ActionPayload(BaseModel):
    assets: list[str] | None
    tool_call: list[Tool] | None


class MainActionResult(BaseModel):
    artifact_id: str
    data: str
    error: str | None = None


class AgentPayload(BaseModel):
    agent: str
    task: str
    references: list[str] = []


class ReAct(BaseModel):
    thought: str
    action: ActionPayload | AgentPayload | None
    results: Any | None
    error: str | None = None


class PlainText(BaseModel):
    result: str
    error: str | None = None
