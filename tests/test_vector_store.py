from memory_service.models import MemoryCreate
from memory_service.vector_store import vector_store


def test_add_and_retrieve_semantic_match():
    vector_store.add(MemoryCreate(text="The user's dog is named Max.", session_id="test-session"))

    results = vector_store.search("what is the user's pet's name?")

    assert any("Max" in hit.text for hit in results)
