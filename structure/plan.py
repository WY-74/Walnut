from pydantic import BaseModel


class Tool(BaseModel):
    Name: str
    Args: dict | None = None


class Task(BaseModel):
    Detail: str
    Tools: list[Tool] | None = None


class Plan(BaseModel):
    Tasks: list[Task] | None = None
    Error: str | None = None
