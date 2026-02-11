import json
from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph.state import CompiledStateGraph
from sse_starlette.sse import EventSourceResponse

from agent.services.api.dependencies import get_agent, get_langfuse_handler
from agent.services.api.routes.utils import (
    convert_messages,
    emit_agent_end,
    emit_agent_start,
    emit_done,
    emit_status,
    emit_token,
    emit_tool_end,
    emit_tool_start,
)
from agent.services.api.schemas import ChatRequest, ChatResponse, Message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    agent: Annotated[CompiledStateGraph, Depends(get_agent)],
    langfuse_handler: Annotated[
        LangfuseCallbackHandler, Depends(get_langfuse_handler)
    ],
) -> ChatResponse:
    result = await agent.ainvoke(
        {"messages": convert_messages(request.messages)},
        config={"callbacks": [langfuse_handler]},
    )
    return ChatResponse(
        message=Message(
            role="assistant", content=result["messages"][-1].content
        )
    )


def clean_tool_result(output: str) -> str:
    """Extract meaningful content from tool output."""
    if not output or not output.strip():
        return "✓ completed"

    if output.startswith("Command("):
        if "ToolMessage(content=" in output:
            start = output.find("'", output.find("ToolMessage(content=")) + 1
            end = output.find("'", start)
            if end > start:
                return output[start:end]
        return "✓ completed"

    if output.startswith("{") or output.startswith("["):
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                for key in ("content", "message", "result"):
                    if key in data:
                        return str(data[key])
            return json.dumps(data, indent=2)
        except json.JSONDecodeError:
            pass

    return output


def extract_text_content(content: Any) -> str:
    """Extract text from various content formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


async def generate_stream(
    agent: CompiledStateGraph,
    messages: list[Message],
    langfuse_handler: LangfuseCallbackHandler,
) -> AsyncGenerator[dict[str, str], None]:
    """Stream typed events for Open WebUI Pipe consumption."""

    tool_info: dict[str, dict] = {}
    subagent_stack: list[str] = []  # Track nested sub-agents

    def get_agent_depth() -> int:
        return len(subagent_stack)

    yield emit_status("Starting...", get_agent_depth())

    async for event in agent.astream_events(
        {"messages": convert_messages(messages)},
        version="v2",
        config={"callbacks": [langfuse_handler]},
    ):
        kind = event["event"]
        run_id = event.get("run_id", "")

        if kind == "on_chat_model_stream":
            content = extract_text_content(event["data"]["chunk"].content)
            if content:
                yield emit_token(content, get_agent_depth())

        elif kind == "on_tool_start":
            tool_name = event.get("name", "tool")
            tool_info[run_id] = {"name": tool_name}

            # Track sub-agent (task tool)
            if tool_name == "task":
                subagent_stack.append(run_id)
                yield emit_agent_start(run_id, tool_name, get_agent_depth())
            else:
                yield emit_tool_start(run_id, tool_name, get_agent_depth())

        elif kind == "on_tool_end" and run_id in tool_info:
            tool_name = tool_info[run_id]["name"]
            tool_output = event["data"].get("output", "")
            output_str = (
                tool_output
                if isinstance(tool_output, str)
                else json.dumps(tool_output, default=str)
            )

            if subagent_stack and subagent_stack[-1] == run_id:
                depth = get_agent_depth()
                subagent_stack.pop()
                yield emit_agent_end(run_id, depth)
                cleaned_result = clean_tool_result(output_str)
                yield emit_tool_end(
                    run_id, tool_name, cleaned_result, get_agent_depth()
                )
            else:
                cleaned_result = clean_tool_result(output_str)
                yield emit_tool_end(
                    run_id, tool_name, cleaned_result, get_agent_depth()
                )

    yield emit_done()


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    agent: Annotated[CompiledStateGraph, Depends(get_agent)],
    langfuse_handler: Annotated[
        LangfuseCallbackHandler, Depends(get_langfuse_handler)
    ],
):
    """Send a message and get a streaming response (SSE) with typed events."""
    return EventSourceResponse(
        generate_stream(agent, request.messages, langfuse_handler),
        media_type="text/event-stream",
    )
