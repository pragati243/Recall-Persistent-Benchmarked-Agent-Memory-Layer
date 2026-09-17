import json

from groq import BadRequestError
from pydantic import BaseModel

from .config import settings
from .llm import get_client, tool_arguments

_TOOL = {
    "type": "function",
    "function": {
        "name": "record_entities",
        "description": "Record entities and relationships mentioned in a memory.",
        "parameters": {
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


def extract(text: str) -> ExtractionResult:
    prompt = f"Extract entities and relationships from this memory:\n\n{text}"
    try:
        response = get_client().chat.completions.create(
            model=settings.extraction_model,
            max_completion_tokens=512,
            tools=[_TOOL],
            tool_choice={"type": "function", "function": {"name": "record_entities"}},
            messages=[{"role": "user", "content": prompt}],
        )
        return ExtractionResult(**tool_arguments(response, "record_entities"))
    except BadRequestError as error:
        if getattr(error, "code", None) != "tool_use_failed":
            raise

    # GPT-OSS can occasionally emit malformed function arguments. JSON mode
    # remains structured and is normalized into the identical downstream schema.
    response = get_client().chat.completions.create(
        model=settings.extraction_model,
        max_completion_tokens=512,
        response_format={"type": "json_object"},
        messages=[{
            "role": "system",
            "content": (
                "Return only a JSON object with keys entities and relationships. "
                "Each entity is {name, type}, where type is person, project, preference, or fact. "
                "Each relationship is {source, target, relation}; relation is a short uppercase verb phrase."
            ),
        }, {"role": "user", "content": prompt}],
    )
    return ExtractionResult(**json.loads(response.choices[0].message.content or "{}"))
