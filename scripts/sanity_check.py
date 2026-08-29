"""Phase 1 sanity check: add a few memories, then confirm semantic retrieval surfaces
the right ones for queries that don't share keywords with the stored text."""

from memory_service.models import MemoryCreate
from memory_service.vector_store import vector_store

SEED_MEMORIES = [
    ("The user's favorite programming language is Python.", "session-1"),
    ("The user is allergic to peanuts.", "session-1"),
    ("The user is building a project called Recall, a memory layer for AI agents.", "session-2"),
]

PROBES = [
    "what food should the agent avoid suggesting?",
    "what is the user building?",
]


def main() -> None:
    for text, session_id in SEED_MEMORIES:
        record = vector_store.add(MemoryCreate(text=text, session_id=session_id))
        print(f"[add] {record.id[:8]}  {record.text}")

    for probe in PROBES:
        print(f"\n--- retrieving: {probe!r} ---")
        for hit in vector_store.search(probe):
            print(f"[hit score={hit.score:.3f}] {hit.text}")


if __name__ == "__main__":
    main()
