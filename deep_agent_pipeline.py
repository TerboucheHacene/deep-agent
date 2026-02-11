"""
title: Deep Agent
author: Deep Agent
version: 0.1.0
description: Pipeline for interacting with the Deep Agent API
"""

import json
from collections.abc import Generator, Iterator

import requests  # type: ignore[import-untyped]
from pydantic import BaseModel, Field


class Pipe:
    """Open WebUI Pipe for Deep Agent."""

    class Valves(BaseModel):
        """Configuration options for the pipe."""

        api_url: str = Field(
            default="http://deep-agent-api:8000",
            description="The base URL of the Deep Agent API (Docker service name)",
        )
        stream: bool = Field(
            default=True,
            description="Enable streaming responses",
        )
        show_tool_details: bool = Field(
            default=True,
            description="Show tool call details in responses (set to False to only show final answer)",
        )

    def __init__(self):
        self.type = "pipe"
        self.name = "Deep Agent"
        self.valves = self.Valves()

    async def on_startup(self):
        """Called when the server starts."""
        print(f"Deep Agent Pipe started. API URL: {self.valves.api_url}")

    async def on_shutdown(self):
        """Called when the server shuts down."""
        print("Deep Agent Pipe shutting down.")

    def pipe(
        self,
        body: dict,
    ) -> str | Generator | Iterator:
        """
        Main pipeline method. Called for each user message.

        Args:
            body: Full request body from Open WebUI

        Returns:
            Response string or generator for streaming
        """
        # Extract messages from body
        messages = body.get("messages", [])

        # Convert messages to our API format
        api_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle content that might be a list (multimodal)
            if isinstance(content, list):
                # Extract text content
                text_parts = [
                    part.get("text", "")
                    for part in content
                    if part.get("type") == "text"
                ]
                content = " ".join(text_parts)

            api_messages.append({"role": role, "content": content})

        # Check if streaming is requested
        stream = body.get("stream", self.valves.stream)

        if stream:
            return self._stream_response(api_messages)
        else:
            return self._get_response(api_messages)

    def _get_response(self, messages: list[dict]) -> str:
        """Get a non-streaming response from the API."""
        try:
            response = requests.post(
                f"{self.valves.api_url}/chat",
                json={
                    "messages": messages,
                    "stream": False,
                    "show_tool_details": self.valves.show_tool_details,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            content: str = data.get("message", {}).get("content", "No response")
            return content
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Deep Agent API: {str(e)}"

    def _stream_response(
        self, messages: list[dict]
    ) -> Generator[str, None, None]:
        """Stream response from the API using SSE."""
        try:
            response = requests.post(
                f"{self.valves.api_url}/chat/stream",
                json={
                    "messages": messages,
                    "stream": True,
                    "show_tool_details": self.valves.show_tool_details,
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    # SSE format: "data: {...}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)
                            if "content" in data:
                                yield data["content"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

        except requests.exceptions.RequestException as e:
            yield f"Error connecting to Deep Agent API: {str(e)}"
