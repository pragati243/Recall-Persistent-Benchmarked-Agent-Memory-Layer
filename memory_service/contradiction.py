from .audit_store import audit_store
from .graph_store import graph_store, normalize_relation

# v1 policy (spec §6.3): a new fact supersedes an older one about the same
# (entity, relation) if it points at a different target. Nothing is deleted —
# the old fact is marked superseded_at and stays in the audit trail.
# Known limitation: matching is on exact normalized relation string, so the
# LLM must extract a consistent relation label for the same kind of fact
# across sessions (e.g. always "PREFERS", not "PREFERS" then "LIKES_BEST").


def apply(
    user_id: str, source_key: str, source_name: str, relation: str,
    target_key: str, target_name: str, memory_id: str,
) -> None:
    relation = normalize_relation(relation)

    for row in audit_store.find_active(user_id, source_key, relation):
        if row["target_key"] == target_key:
            continue  # same fact restated, not a contradiction
        audit_store.supersede(row["id"], memory_id)
        graph_store.supersede_relationship(user_id, source_key, row["target_key"], relation)

    graph_store.upsert_relationship(user_id, source_key, target_key, relation, memory_id)
    audit_store.record(user_id, source_key, source_name, relation, target_key, target_name, memory_id)
