"""Phase 3 sanity check: add a fact, add a contradicting fact, confirm
retrieval surfaces the CURRENT one and the audit trail preserves both,
with the old one marked superseded."""

from memory_service.audit_store import audit_store
from memory_service.graph_store import normalize_name
from memory_service.memory_manager import add_memory
from memory_service.models import MemoryCreate
from memory_service.retrieval_router import retrieval_router

USER = "phase3-demo-user"
ENTITY = "the user"  # depends on how the LLM names the subject entity — see README caveat

MEMORIES = [
    ("The user prefers email notifications.", "s1"),
    ("The user now prefers SMS notifications instead.", "s2"),
]


def main() -> None:
    for text, session_id in MEMORIES:
        add_memory(MemoryCreate(text=text, session_id=session_id, user_id=USER))

    print("--- retrieval: 'how does the user want to be notified?' ---")
    result = retrieval_router.retrieve("how does the user want to be notified?", user_id=USER)
    print(f"mode: {result['mode']}")
    for hit in result["graph_hits"]:
        print(f"[graph] {hit['name']} ({hit['type']})")
    for hit in result["vector_hits"]:
        print(f"[vector score={hit.score:.3f}] {hit.text}")

    print(f"\n--- audit trail for entity_key={normalize_name(ENTITY)!r} ---")
    for row in audit_store.history(USER, normalize_name(ENTITY)):
        status = "SUPERSEDED" if row["superseded_at"] else "ACTIVE"
        print(f"[{status}] {row['relation']} -> {row['target_name']}  (memory_id={row['memory_id'][:8]})")


if __name__ == "__main__":
    main()
