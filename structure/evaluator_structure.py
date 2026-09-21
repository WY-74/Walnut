from pydantic import BaseModel


class EvaluatorResult(BaseModel):
    available: bool
    info_error: str | None
    error: str | None = None
