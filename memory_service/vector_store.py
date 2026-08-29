from datetime import datetime, timezone
from uuid import uuid4

from qdrant_client import QdrantClient, models

from .config import settings
from .models import MemoryCreate, MemoryRecord


class VectorStore:
    """Thin wrapper around Qdrant's local-inference API (FastEmbed under the hood)."""

    def __init__(self) -> None:
        self._client = QdrantClient(path=settings.qdrant_path)
        self._model = settings.embedding_model
        if not self._client.collection_exists(settings.qdrant_collection):
            self._client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=self._client.get_embedding_size(self._model),
                    distance=models.Distance.COSINE,
                ),
            )

    def add(self, memory: MemoryCreate) -> MemoryRecord:
        memory_id = str(uuid4())
        payload = {
            "text": memory.text,
            "session_id": memory.session_id,
            "user_id": memory.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._client.upload_collection(
            collection_name=settings.qdrant_collection,
            vectors=[models.Document(text=memory.text, model=self._model)],
            payload=[payload],
            ids=[memory_id],
        )
        return MemoryRecord(id=memory_id, score=None, **payload)

    def search(self, query: str, user_id: str = "default_user", limit: int = 5) -> list[MemoryRecord]:
        hits = self._client.query_points(
            collection_name=settings.qdrant_collection,
            query=models.Document(text=query, model=self._model),
            query_filter=models.Filter(
                must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))]
            ),
            limit=limit,
        ).points
        return [MemoryRecord(id=str(hit.id), score=hit.score, **hit.payload) for hit in hits]


vector_store = VectorStore()
