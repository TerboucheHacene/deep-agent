import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.services.api.schemas import Message

MESSAGE_MAP = {
    "user": HumanMessage,
    "assistant": AIMessage,
    "system": SystemMessage,
}


def convert_messages(messages: list[Message]):
    return [
        MESSAGE_MAP[msg.role](content=msg.content)
        for msg in messages
        if msg.role in MESSAGE_MAP
    ]


def emit_event(
    event_type: str, data: dict[str, Any] | None = None
) -> dict[str, str]:
    """Create a typed SSE event dict for EventSourceResponse."""
    event: dict[str, Any] = {"type": event_type}
    if data:
        event["data"] = data
    return {"data": json.dumps(event)}


def emit_status(description: str, agent_depth: int = 0) -> dict[str, str]:
    return emit_event(
        "status", {"description": description, "agent_depth": agent_depth}
    )


def emit_tool_start(
    tool_id: str, name: str, agent_depth: int = 0
) -> dict[str, str]:
    return emit_event(
        "tool_start",
        {"tool_id": tool_id, "name": name, "agent_depth": agent_depth},
    )


def emit_tool_end(
    tool_id: str, name: str, result: str, agent_depth: int = 0
) -> dict[str, str]:
    return emit_event(
        "tool_end",
        {
            "tool_id": tool_id,
            "name": name,
            "result": result,
            "agent_depth": agent_depth,
        },
    )


def emit_token(content: str, agent_depth: int = 0) -> dict[str, str]:
    return emit_event("token", {"content": content, "agent_depth": agent_depth})


def emit_agent_start(agent_id: str, name: str, depth: int) -> dict[str, str]:
    return emit_event(
        "agent_start", {"agent_id": agent_id, "name": name, "depth": depth}
    )


def emit_agent_end(agent_id: str, depth: int) -> dict[str, str]:
    return emit_event("agent_end", {"agent_id": agent_id, "depth": depth})


def emit_done() -> dict[str, str]:
    return emit_event("done")
