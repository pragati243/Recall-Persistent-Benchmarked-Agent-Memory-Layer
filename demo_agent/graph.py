from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from memory_service.config import settings
from memory_service.llm import get_client
from memory_service.retrieval_router import retrieval_router

# Single scenario per spec §6.5: a personal assistant that schedules tasks and
# remembers preferences. Kept intentionally simple - it exists to prove the
# memory layer works end-to-end, not to be a sophisticated agent on its own.
SYSTEM_PROMPT = (
    "You are a personal assistant that helps the user schedule tasks and "
    "remembers their preferences. Use the remembered context below if it's "
    "relevant to the conversation; ignore it otherwise.\n\nRemembered context:\n{context}"
)


class AgentState(TypedDict):
    user_id: str
    messages: list[dict]  # [{"role": "user" | "assistant", "content": str}]
    context: str


def retrieve(state: AgentState) -> AgentState:
    if state["context"]:
        return state  # already loaded this session - retrieval happens once, at session start
    query = state["messages"][0]["content"]
    result = retrieval_router.retrieve(query, user_id=state["user_id"])
    lines = [hit.text for hit in result["vector_hits"]]
    lines += [f"{hit['name']} ({hit['type']})" for hit in result["graph_hits"]]
    return {**state, "context": "\n".join(lines) or "(no prior memory found)"}


def chat(state: AgentState) -> AgentState:
    response = get_client().messages.create(
        model=settings.agent_model,
        max_tokens=512,
        system=SYSTEM_PROMPT.format(context=state["context"]),
        messages=state["messages"],
    )
    reply = "".join(block.text for block in response.content if block.type == "text")
    return {**state, "messages": [*state["messages"], {"role": "assistant", "content": reply}]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("chat", chat)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "chat")
    graph.add_edge("chat", END)
    return graph.compile()


agent_graph = build_graph()


def summarize_session(messages: list[dict]) -> str:
    """One-shot, end-of-session call (not a graph node) - the non-goal in the
    spec is live mid-conversation memory writes, not a summary written once
    the session is over."""
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    response = get_client().messages.create(
        model=settings.extraction_model,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                "Summarize any durable facts about the user worth remembering from this "
                "conversation (preferences, projects, people, decisions). One to three "
                "short sentences, no preamble.\n\n" + transcript
            ),
        }],
    )
    return "".join(block.text for block in response.content if block.type == "text")
