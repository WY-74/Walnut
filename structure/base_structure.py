from typing import Any
from pydantic import BaseModel


class Tool(BaseModel):
    target: str
    name: str
    args: dict | None


class ActionPayload(BaseModel):
    assets: list[str] | None
    tool_call: list[Tool] | None


class ReAct(BaseModel):
    thought: str
    action: ActionPayload | None
    results: Any | None
    error: str | None = None


class PlainText(BaseModel):
    result: str
    error: str | None = None
