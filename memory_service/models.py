from pydantic import BaseModel


class MemoryCreate(BaseModel):
    text: str
    session_id: str
    user_id: str = "default_user"


class MemoryRecord(BaseModel):
    id: str
    text: str
    session_id: str
    user_id: str
    created_at: str
    score: float | None = None
