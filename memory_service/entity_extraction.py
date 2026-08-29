from anthropic import Anthropic
from pydantic import BaseModel

from .config import settings

_TOOL = {
    "name": "record_entities",
    "description": "Record entities and relationships mentioned in a memory.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string", "enum": ["person", "project", "preference", "fact"]},
                    },
                    "required": ["name", "type"],
                },
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "relation": {"type": "string", "description": "short verb phrase, e.g. MANAGES, PREFERS"},
                    },
                    "required": ["source", "target", "relation"],
                },
            },
        },
        "required": ["entities", "relationships"],
    },
}


class ExtractedEntity(BaseModel):
    name: str
    type: str


class ExtractedRelationship(BaseModel):
    source: str
    target: str
    relation: str


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]


_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=settings.anthropic_api_key)
    return _client


def extract(text: str) -> ExtractionResult:
    response = _get_client().messages.create(
        model=settings.extraction_model,
        max_tokens=512,
        tools=[_TOOL],
        tool_choice={"type": "tool", "name": "record_entities"},
        messages=[{"role": "user", "content": f"Extract entities and relationships from this memory:\n\n{text}"}],
    )
    tool_call = next(block for block in response.content if block.type == "tool_use")
    return ExtractionResult(**tool_call.input)
