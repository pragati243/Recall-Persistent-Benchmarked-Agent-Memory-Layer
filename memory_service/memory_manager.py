from . import contradiction
from .entity_extraction import extract
from .graph_store import graph_store
from .models import MemoryCreate, MemoryRecord
from .vector_store import vector_store


def add_memory(memory: MemoryCreate) -> MemoryRecord:
    record = vector_store.add(memory)

    extraction = extract(memory.text)
    keys: dict[str, str] = {}
    for entity in extraction.entities:
        keys[entity.name] = graph_store.upsert_entity(memory.user_id, entity.name, entity.type)

    def _key_for(name: str) -> str:
        # LLM relations sometimes reference a name it didn't list as an entity
        # (e.g. an implicit "the user") — link it on the fly as a generic fact.
        if name not in keys:
            keys[name] = graph_store.upsert_entity(memory.user_id, name, "fact")
        return keys[name]

    for rel in extraction.relationships:
        contradiction.apply(
            user_id=memory.user_id,
            source_key=_key_for(rel.source),
            source_name=rel.source,
            relation=rel.relation,
            target_key=_key_for(rel.target),
            target_name=rel.target,
            memory_id=record.id,
        )

    return record
