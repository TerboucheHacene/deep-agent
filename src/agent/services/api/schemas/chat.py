from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    stream: bool = False
    show_tool_details: bool = True  # Set to False to hide tool call details


class ChatResponse(BaseModel):
    message: Message
