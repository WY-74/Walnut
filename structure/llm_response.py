from pydantic import BaseModel


class ActionPayload(BaseModel):
    Assets: list[str] | None = None
    ToolCall: list[str] | None = None


class LLMResponse(BaseModel):
    Available: bool = True
    Thought: str
    Action: ActionPayload | None = None
    Results: str | dict | None = None
    RawErrorResponse: str | None = None
