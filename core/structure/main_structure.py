from pydantic import BaseModel

__all__ = ["MainObservation"]


class MainObservation(BaseModel):
    artifact_id: str
    data: str
    error: str | None = None
