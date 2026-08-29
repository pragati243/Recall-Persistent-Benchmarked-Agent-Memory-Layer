"""Phase 2 sanity check: prove graph traversal answers a 2-hop relationship
question that vector similarity alone can't, because no single sentence
mentions both endpoints."""

from memory_service.memory_manager import add_memory
from memory_service.models import MemoryCreate
from memory_service.retrieval_router import retrieval_router
from memory_service.vector_store import vector_store

USER = "phase2-demo-user"

MEMORIES = [
    "Sarah manages the Atlas project.",
    "Raj is the tech lead on the Atlas project.",
    "Atlas is expected to ship in November.",
]

QUERY = "Who does Raj report to?"


def main() -> None:
    for text in MEMORIES:
        add_memory(MemoryCreate(text=text, session_id="s1", user_id=USER))

    print("--- vector-only search ---")
    for hit in vector_store.search(QUERY, user_id=USER):
        print(f"[score={hit.score:.3f}] {hit.text}")

    print("\n--- retrieval router (hybrid: graph + vector) ---")
    result = retrieval_router.retrieve(QUERY, user_id=USER)
    print(f"mode: {result['mode']}")
    for hit in result["graph_hits"]:
        print(f"[graph] {hit['name']} ({hit['type']})")
    for hit in result["vector_hits"]:
        print(f"[vector score={hit.score:.3f}] {hit.text}")


if __name__ == "__main__":
    main()
