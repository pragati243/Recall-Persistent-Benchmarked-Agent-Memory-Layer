import json

from groq import Groq

from .config import settings

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def tool_arguments(response: object, tool_name: str) -> dict:
    """Normalize an OpenAI-compatible function call to the extraction input schema."""
    message = response.choices[0].message
    for call in message.tool_calls or []:
        if call.function.name == tool_name:
            arguments = json.loads(call.function.arguments)
            if not isinstance(arguments, dict):
                raise ValueError(f"{tool_name} returned non-object arguments")
            return arguments
    raise ValueError(f"Groq did not return the required {tool_name} tool call")
