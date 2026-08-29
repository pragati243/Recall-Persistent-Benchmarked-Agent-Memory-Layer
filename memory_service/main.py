from fastapi import FastAPI

from .models import MemoryCreate, MemoryRecord
from .vector_store import vector_store

app = FastAPI(title="Recall Memory Service", version="0.1.0")


@app.post("/memory/add", response_model=MemoryRecord)
def add_memory(memory: MemoryCreate) -> MemoryRecord:
    return vector_store.add(memory)


@app.get("/memory/retrieve", response_model=list[MemoryRecord])
def retrieve_memory(query: str, user_id: str = "default_user", limit: int = 5) -> list[MemoryRecord]:
    return vector_store.search(query, user_id=user_id, limit=limit)
