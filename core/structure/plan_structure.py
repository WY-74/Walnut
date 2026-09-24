from pydantic import BaseModel
from .base_structure import Tool

__all__ = ["Task", "PlanResult"]


class Task(BaseModel):
    detail: str
    tools: list[Tool] | None
    save: bool


class PlanResult(BaseModel):
    tasks: list[Task] | dict | None
    info_error: str | None
    error: str | None = None
