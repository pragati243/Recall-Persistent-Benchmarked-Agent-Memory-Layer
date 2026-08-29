from datetime import datetime
from uuid import UUID

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


class GraphNeighbor(BaseModel):
    name: str
    type: str


class RetrievalResult(BaseModel):
    mode: str
    vector_results: list[MemoryRecord]
    graph_results: list[GraphNeighbor]


class AuditEntry(BaseModel):
    id: UUID
    entity_key: str
    entity_name: str
    relation: str
    target_key: str
    target_name: str
    memory_id: str
    created_at: datetime
    superseded_at: datetime | None = None
    superseded_by_memory_id: str | None = None
