from fastapi import FastAPI

from .audit_store import audit_store
from .graph_store import normalize_name
from .memory_manager import add_memory as _add_memory
from .models import AuditEntry, GraphNeighbor, MemoryCreate, MemoryRecord, RetrievalResult
from .retrieval_router import retrieval_router

app = FastAPI(title="Recall Memory Service", version="0.1.0")


@app.post("/memory/add", response_model=MemoryRecord)
def add_memory(memory: MemoryCreate) -> MemoryRecord:
    return _add_memory(memory)


@app.get("/memory/retrieve", response_model=RetrievalResult)
def retrieve_memory(query: str, user_id: str = "default_user", limit: int = 5) -> RetrievalResult:
    result = retrieval_router.retrieve(query, user_id=user_id, limit=limit)
    return RetrievalResult(
        mode=result["mode"],
        vector_results=result["vector_hits"],
        graph_results=[GraphNeighbor(**hit) for hit in result["graph_hits"]],
    )


@app.get("/memory/audit/{entity}", response_model=list[AuditEntry])
def get_audit(entity: str, user_id: str = "default_user") -> list[AuditEntry]:
    return audit_store.history(user_id, normalize_name(entity))
