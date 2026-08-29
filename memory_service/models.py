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
