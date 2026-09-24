from pydantic import BaseModel

__all__ = ["ToolCallObservation", "ToolCallStepResult", "ToolCallResult"]


class ToolCallObservation(BaseModel):
    result: str
    error: str | None = None


class ToolCallStepResult(BaseModel):
    result: str
    error: str | None = None


class ToolCallResult(BaseModel):
    result: dict[int, ToolCallStepResult]
    error: str | None = None
