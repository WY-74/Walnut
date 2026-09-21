from pydantic import BaseModel


class Tool(BaseModel):
    target: str
    name: str
    args: dict | None


class Task(BaseModel):
    detail: str
    tools: list[Tool] | None
    save: bool


class Plan(BaseModel):
    tasks: list[Task] | dict | None
    info_error: str | None
    error: str | None = None
