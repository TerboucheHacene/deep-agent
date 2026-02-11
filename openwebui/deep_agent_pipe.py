"""
title: Deep Agent Pipe
author: TERBOUCHE Hacene
version: 1.0.0
license: MIT
description: A pipe that connects Open WebUI to the Deep Agent backend,
             routing typed events to native UI components (status bar, citations, chat).
requirements: httpx
"""

import json
from collections.abc import AsyncGenerator

import httpx
from pydantic import BaseModel, Field


class Pipe:
    """Deep Agent Pipe for Open WebUI.

    Routes typed events from the Deep Agent backend to Open WebUI UI components:
    - status → Status bar (thinking indicator)
    - tool_start → Status bar update
    - tool_end → Citation (clickable tool result)
    - token → Chat bubble (streamed text)
    - agent_start → Status bar (sub-agent indicator)
    - agent_end → Status bar update
    - done → Finalize status bar
    """

    class Valves(BaseModel):
        DEEP_AGENT_URL: str = Field(
            default="http://deep-agent-api:8000",
            description="Base URL for the Deep Agent backend API.",
        )
        SHOW_TOOL_CITATIONS: bool = Field(
            default=True,
            description="Show tool results as clickable citations.",
        )
        SHOW_SUBAGENT_STATUS: bool = Field(
            default=True,
            description="Show sub-agent activity in status bar.",
        )
        REQUEST_TIMEOUT: int = Field(
            default=300,
            description="Request timeout in seconds for long-running agent tasks.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def pipe(
        self,
        body: dict,
        __event_emitter__=None,
    ) -> AsyncGenerator[str, None]:
        """Process chat request and route events to Open WebUI.

        Args:
            body: The request body containing messages and settings.
            __event_emitter__: Open WebUI's event emitter for status/citation events.

        Yields:
            Token content strings to be displayed in the chat bubble.
        """
        messages = body.get("messages", [])
        if not messages:
            yield "Error: No messages provided."
            return

        payload = {"messages": messages, "stream": True}

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.valves.REQUEST_TIMEOUT)
            ) as client:
                async with client.stream(
                    "POST",
                    f"{self.valves.DEEP_AGENT_URL}/chat/stream",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        yield f"Error: Backend returned {response.status_code}: {error_text.decode()}"
                        return

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue

                        # Parse the SSE data
                        try:
                            data_str = line[5:].strip()  # Remove "data:" prefix
                            if not data_str:
                                continue
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        event_type = event.get("type")
                        event_data = event.get("data", {})

                        if event_type == "status":
                            await self._handle_status(
                                event_data, __event_emitter__
                            )

                        elif event_type == "tool_start":
                            await self._handle_tool_start(
                                event_data, __event_emitter__
                            )

                        elif event_type == "tool_end":
                            await self._handle_tool_end(
                                event_data, __event_emitter__
                            )

                        elif event_type == "token":
                            agent_depth = event_data.get("agent_depth", 0)
                            if agent_depth == 0:
                                yield event_data.get("content", "")

                        elif event_type == "agent_start":
                            await self._handle_agent_start(
                                event_data, __event_emitter__
                            )

                        elif event_type == "agent_end":
                            await self._handle_agent_end(
                                event_data, __event_emitter__
                            )

                        elif event_type == "done":
                            await self._handle_done(__event_emitter__)

        except httpx.ConnectError:
            yield f"Error: Could not connect to Deep Agent backend at {self.valves.DEEP_AGENT_URL}"
        except httpx.TimeoutException:
            yield "Error: Request timed out. The agent may still be processing."
        except Exception as e:
            yield f"Error: {str(e)}"

        # Ensure status is finalized
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Complete", "done": True},
                }
            )

    async def _handle_status(self, data: dict, event_emitter) -> None:
        """Handle status events → Status bar."""
        if not event_emitter:
            return

        description = data.get("description", "Processing...")
        agent_depth = data.get("agent_depth", 0)

        # Add depth indicator for nested agents
        if agent_depth > 0:
            description = f"↳ {description}"

        await event_emitter(
            {
                "type": "status",
                "data": {"description": description, "done": False},
            }
        )

    async def _handle_tool_start(self, data: dict, event_emitter) -> None:
        """Handle tool_start events → Status bar update."""
        if not event_emitter:
            return

        tool_name = data.get("name", "tool")
        agent_depth = data.get("agent_depth", 0)

        prefix = "↳ " if agent_depth > 0 else ""
        description = f"{prefix}🔧 Running {tool_name}..."

        await event_emitter(
            {
                "type": "status",
                "data": {"description": description, "done": False},
            }
        )

    async def _handle_tool_end(self, data: dict, event_emitter) -> None:
        """Handle tool_end events → Citation (if enabled).

        Only main agent tools (agent_depth == 0) are shown as citations.
        Sub-agent tools are grouped under the parent 'task' tool.
        """
        if not event_emitter or not self.valves.SHOW_TOOL_CITATIONS:
            return

        agent_depth = data.get("agent_depth", 0)
        if agent_depth > 0:
            return

        tool_id = data.get("tool_id", "")
        tool_name = data.get("name", "tool")
        result = data.get("result", "")

        if not result or result == "✓ completed":
            return

        # Create citation with preview and full content
        preview = result[:500] if len(result) > 500 else result

        await event_emitter(
            {
                "type": "source",
                "data": {
                    "source": {
                        "name": f"🔧 {tool_name}",
                        "id": tool_id,
                    },
                    "document": [preview],
                    "metadata": [
                        {
                            "full_result": result,
                            "tool_name": tool_name,
                            "tool_id": tool_id,
                        }
                    ],
                },
            }
        )

    async def _handle_agent_start(self, data: dict, event_emitter) -> None:
        """Handle agent_start events → Status bar (sub-agent indicator)."""
        if not event_emitter or not self.valves.SHOW_SUBAGENT_STATUS:
            return

        agent_name = data.get("name", "sub-agent")
        depth = data.get("depth", 1)

        prefix = "↳ " * depth
        description = f"{prefix}🤖 Starting {agent_name}..."

        await event_emitter(
            {
                "type": "status",
                "data": {"description": description, "done": False},
            }
        )

    async def _handle_agent_end(self, data: dict, event_emitter) -> None:
        """Handle agent_end events → Status bar update."""
        if not event_emitter or not self.valves.SHOW_SUBAGENT_STATUS:
            return

        depth = data.get("depth", 1)
        prefix = "↳ " * (depth - 1) if depth > 1 else ""
        description = f"{prefix}Sub-agent completed"

        await event_emitter(
            {
                "type": "status",
                "data": {"description": description, "done": True},
            }
        )

    async def _handle_done(self, event_emitter) -> None:
        """Handle done events → Finalize status bar."""
        if not event_emitter:
            return

        await event_emitter(
            {
                "type": "status",
                "data": {"description": "Complete", "done": True},
            }
        )
