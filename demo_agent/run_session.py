"""Simulate one conversation session against the demo agent - retrieve_memory
at session start, chat turn by turn, add_memory once at session end."""

from uuid import uuid4

from demo_agent.graph import agent_graph, summarize_session
from memory_service.memory_manager import add_memory
from memory_service.models import MemoryCreate


def main() -> None:
    user_id = input("user id [demo-user]: ").strip() or "demo-user"
    session_id = uuid4().hex[:8]
    print(f"session {session_id} — type 'exit' to end\n")

    state = {"user_id": user_id, "messages": [], "context": ""}
    while True:
        user_input = input("you: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        state["messages"].append({"role": "user", "content": user_input})
        state = agent_graph.invoke(state)
        print(f"assistant: {state['messages'][-1]['content']}\n")

    if len(state["messages"]) < 2:
        print("\n[session ended - nothing to remember]")
        return

    summary = summarize_session(state["messages"])
    add_memory(MemoryCreate(text=summary, session_id=session_id, user_id=user_id))
    print(f"\n[session ended - stored to memory]: {summary}")


if __name__ == "__main__":
    main()
