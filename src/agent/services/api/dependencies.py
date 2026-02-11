from functools import lru_cache

from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph.state import CompiledStateGraph

from agent.ai.assistant import build_assistant_agent


@lru_cache(maxsize=1)
def get_agent() -> CompiledStateGraph:
    """Get or create the agent instance (singleton)."""
    return build_assistant_agent()


def get_langfuse_handler() -> LangfuseCallbackHandler:
    """Get a new Langfuse callback handler for each request."""
    return LangfuseCallbackHandler()
