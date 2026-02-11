from datetime import datetime

from langchain.messages import (
    SystemMessage,
)
from langchain_anthropic import ChatAnthropic
from langfuse.langchain import CallbackHandler as LangfuseCallbackHandler
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.ai.prompts import (
    FILE_USAGE_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    SUBAGENT_USAGE_INSTRUCTIONS,
    TODO_USAGE_INSTRUCTIONS,
)
from agent.ai.state import DeepAgentState
from agent.ai.tools import (
    SubAgent,
    create_task_tool,
    ls,
    read_file,
    read_todos,
    tavily_search,
    think_tool,
    write_file,
    write_todos,
)
from agent.ai.tools.research_tools import get_today_str


def build_subagents():
    research_sub_agent: SubAgent = {
        "name": "research-agent",
        "description": "Delegate research to the sub-agent researcher. Only give this researcher one topic at a time.",
        "prompt": RESEARCHER_INSTRUCTIONS.format(date=get_today_str()),
        "tools": ["tavily_search", "think_tool"],
    }

    task_tool = create_task_tool(
        tools=[tavily_search, think_tool],
        subagents=[research_sub_agent],
        model=ChatAnthropic(
            model="claude-sonnet-4-5-20250929", temperature=0.0
        ),
        state_schema=DeepAgentState,
    )
    return [task_tool]


def build_assistant_agent():
    model = ChatAnthropic(model="claude-sonnet-4-5-20250929", temperature=0.0)
    tools = [
        ls,
        read_file,
        write_file,
        read_todos,
        write_todos,
    ] + build_subagents()
    model = model.bind_tools(tools)

    # Limits
    max_concurrent_research_units = 3
    max_researcher_iterations = 3

    # Build prompt
    SUBAGENT_INSTRUCTIONS = SUBAGENT_USAGE_INSTRUCTIONS.format(
        max_concurrent_research_units=max_concurrent_research_units,
        max_researcher_iterations=max_researcher_iterations,
        date=datetime.now().strftime("%a %b %-d, %Y"),
    )
    INSTRUCTIONS = (
        "# TODO MANAGEMENT\n"
        + TODO_USAGE_INSTRUCTIONS
        + "\n\n"
        + "=" * 80
        + "\n\n"
        + "# FILE SYSTEM USAGE\n"
        + FILE_USAGE_INSTRUCTIONS
        + "\n\n"
        + "=" * 80
        + "\n\n"
        + "# SUB-AGENT DELEGATION\n"
        + SUBAGENT_INSTRUCTIONS
    )

    # Initialize Langfuse handler for full graph tracing
    langfuse_handler = LangfuseCallbackHandler()

    def llm_node(state: MessagesState):
        system_message = SystemMessage(content=INSTRUCTIONS)
        messages = [system_message] + state["messages"]
        response = model.invoke(messages)
        return {"messages": [response]}

    tools_node = ToolNode(tools=tools)

    graph = StateGraph(DeepAgentState)
    graph.add_node("llm_node", llm_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "llm_node")
    graph.add_conditional_edges("llm_node", tools_condition)
    graph.add_edge("tools", "llm_node")

    # Compile and attach callbacks to the entire graph
    assistant = graph.compile().with_config({"callbacks": [langfuse_handler]})

    return assistant
