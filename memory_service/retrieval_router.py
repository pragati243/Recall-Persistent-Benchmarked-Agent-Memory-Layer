from .graph_store import GraphStore, graph_store
from .vector_store import VectorStore, vector_store

# Rule-based, not an ML classifier: cheap, predictable, and easy to explain —
# consistent with keeping "decisions" explicit rather than learned for v1.
_RELATIONSHIP_KEYWORDS = (
    "who", "which", "report to", "works with", "works on",
    "related to", "connected to", "manages", "same project", "same team",
)


class RetrievalRouter:
    def __init__(self, vector_store: VectorStore, graph_store: GraphStore) -> None:
        self._vector_store = vector_store
        self._graph_store = graph_store

    def retrieve(self, query: str, user_id: str = "default_user", limit: int = 5) -> dict:
        wants_relationship = any(kw in query.lower() for kw in _RELATIONSHIP_KEYWORDS)
        matched_entity = self._graph_store.find_entity_by_mention(user_id, query) if wants_relationship else None

        graph_hits = self._graph_store.neighbors(user_id, matched_entity, hops=2) if matched_entity else []
        vector_hits = self._vector_store.search(query, user_id=user_id, limit=limit)

        mode = "graph" if graph_hits else "vector"
        return {"mode": mode, "graph_hits": graph_hits, "vector_hits": vector_hits}


retrieval_router = RetrievalRouter(vector_store, graph_store)
