from pydantic import BaseModel


class Tool(BaseModel):
    Name: str
    Args: str | None = None


class Task(BaseModel):
    Detail: str
    Tools: list[Tool] | None = None


class Plan(BaseModel):
    Tasks: list[Task] | None = None
    MissingInfo: str | None = None
