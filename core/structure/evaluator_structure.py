from pydantic import BaseModel

__all__ = ["EvaluatorResult"]


class EvaluatorResult(BaseModel):
    available: bool
    info_error: str | None
    error: str | None = None
