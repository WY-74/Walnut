from pydantic import BaseModel


class ToolCallObservation(BaseModel):
    result: str
    error: str | None = None


class ToolCallResult(BaseModel):
    result: str
    error: str | None = None
