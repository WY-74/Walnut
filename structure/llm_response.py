from pydantic import BaseModel


class Tool(BaseModel):
    target: str
    name: str
    args: dict | None = None


class ActionPayload(BaseModel):
    assets: list[str] | None = None
    tool_call: list[Tool] | None = None


class LLMResponse(BaseModel):
    available: bool = True
    thought: str
    action: ActionPayload | None = None
    results: str | dict | None = None
    raw_error_response: str | None = None
