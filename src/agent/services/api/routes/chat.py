import html
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph.state import CompiledStateGraph
from sse_starlette.sse import EventSourceResponse

from agent.services.api.dependencies import get_agent, get_langfuse_handler
from agent.services.api.schemas import ChatRequest, ChatResponse, Message

router = APIRouter(prefix="/chat", tags=["chat"])

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


def truncate(text: str, max_len: int = 200) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def clean_tool_result(output: str) -> str:
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
                for key in ("content", "message"):
                    if key in data:
                        return str(data[key])[:200]
            return "✓ completed"
        except json.JSONDecodeError:
            pass

    return output


def format_tool_result(name: str, result: str) -> str:
    preview = html.escape(truncate(clean_tool_result(result)))
    return f"**🔧 {name}:** {preview}\n\n"


def extract_text_content(content) -> str:
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
    show_tool_details: bool = True,
) -> AsyncGenerator[str, None]:
    """Stream with real-time tokens. Final AI duplicated outside collapse."""

    current_ai_content = ""
    tool_info: dict[str, dict] = {}
    collapse_open = False
    streaming_ai = False
    subagent_stack: list[str] = []

    async for event in agent.astream_events(
        {"messages": convert_messages(messages)},
        version="v2",
        config={"callbacks": [langfuse_handler]},
    ):
        kind = event["event"]
        run_id = event.get("run_id")

        if kind == "on_chat_model_stream":
            content = extract_text_content(event["data"]["chunk"].content)
            if content:
                current_ai_content += content

                if show_tool_details:
                    if not collapse_open:
                        yield json.dumps(
                            {
                                "content": "\n<details open>\n<summary>🔍 Execution Steps</summary>\n\n"
                            }
                        )
                        collapse_open = True

                    if not streaming_ai:
                        prefix = (
                            "**🔧 Sub-agent:** "
                            if subagent_stack
                            else "**🤖 AI:** "
                        )
                        yield json.dumps({"content": prefix})
                        streaming_ai = True

                    yield json.dumps({"content": content})

        elif kind == "on_tool_start":
            tool_name = event.get("name", "tool")
            tool_info[run_id] = {"name": tool_name}

            if show_tool_details:
                if streaming_ai:
                    yield json.dumps({"content": "\n\n"})
                    streaming_ai = False
                current_ai_content = ""

                if not collapse_open:
                    yield json.dumps(
                        {
                            "content": "\n<details open>\n<summary>🔍 Execution Steps</summary>\n\n"
                        }
                    )
                    collapse_open = True

            if tool_name == "task":
                subagent_stack.append(run_id)

        elif kind == "on_tool_end" and run_id in tool_info:
            tool_output = event["data"].get("output", "")
            output_str = (
                tool_output
                if isinstance(tool_output, str)
                else json.dumps(tool_output, default=str)
            )
            tool_name = tool_info[run_id]["name"]

            if subagent_stack and subagent_stack[-1] == run_id:
                subagent_stack.pop()
                continue

            if show_tool_details:
                if streaming_ai:
                    yield json.dumps({"content": "\n\n"})
                    streaming_ai = False

                if not collapse_open:
                    yield json.dumps(
                        {
                            "content": "\n<details open>\n<summary>🔍 Execution Steps</summary>\n\n"
                        }
                    )
                    collapse_open = True

                yield json.dumps(
                    {"content": format_tool_result(tool_name, output_str)}
                )

    if streaming_ai:
        yield json.dumps({"content": "\n\n"})

    if collapse_open:
        yield json.dumps({"content": "\n</details>\n\n"})

    if current_ai_content.strip():
        yield json.dumps({"content": current_ai_content})

    yield json.dumps({"done": True})


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    agent: Annotated[CompiledStateGraph, Depends(get_agent)],
    langfuse_handler: Annotated[
        LangfuseCallbackHandler, Depends(get_langfuse_handler)
    ],
):
    """Send a message and get a streaming response (SSE)."""
    return EventSourceResponse(
        generate_stream(
            agent,
            request.messages,
            langfuse_handler,
            show_tool_details=request.show_tool_details,
        ),
        media_type="text/event-stream",
    )
