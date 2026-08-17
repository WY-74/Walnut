from pydantic import BaseModel


class Tool(BaseModel):
    name: str
    args: dict | None = None


class Task(BaseModel):
    detail: str
    tools: list[Tool] | None = None


class Plan(BaseModel):
    tasks: list[Task] | None = None
    error: str | None = None
