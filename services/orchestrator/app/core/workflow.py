"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Annotated, Any, Dict, List, TypedDict  # noqa: F401
from langgraph.graph import Graph, StateGraph
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langchain_core.messages import HumanMessage, SystemMessage
import json

from app.core.config import get_settings

settings = get_settings()


class AgentState(TypedDict):
    """State definition for the agent workflow."""

    messages: List[BaseMessage]
    current_step: str
    task_status: Dict[str, Any]
    context: Dict[str, Any]


def create_agent_workflow() -> Graph:
    """
    Creates the main agent workflow using LangGraph.

    The workflow implements the Model Context Protocol and handles:
    1. Task Planning
    2. Web Search (conditional)
    3. Document Processing (conditional)
    4. LLM Interactions
    5. Response Generation
    """
    # Initialize the state graph
    workflow = StateGraph(AgentState)

    # Define the nodes (agents)
    def task_planner(state: AgentState) -> AgentState:
        """Plans the execution steps for a given task."""
        llm = ChatOpenAI(
            temperature=0,
            model_name=settings.model_name,
            openai_api_key=settings.openai_api_key,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a task planning agent that breaks down user requests into actionable steps. "
                    "Determine if the task requires web search or document processing. "
                    "Return a JSON with 'needs_web_search' and 'needs_document_processing' boolean fields.",
                ),
                ("human", "{input}"),
            ]
        )
        chain = prompt | llm

        # Get the task from state
        task = state["messages"][-1].content

        # Generate plan and parse the response
        plan = chain.invoke({"input": task})
        try:
            plan_data = json.loads(plan.content)
            state["task_status"]["needs_web_search"] = plan_data.get(
                "needs_web_search", False
            )
            state["task_status"]["needs_document_processing"] = plan_data.get(
                "needs_document_processing", False
            )
        except json.JSONDecodeError:
            # Default to no additional processing if parsing fails
            state["task_status"]["needs_web_search"] = False
            state["task_status"]["needs_document_processing"] = False

        return state

    def web_searcher(state: AgentState) -> AgentState:
        """Performs web search based on the task requirements."""
        llm = ChatOpenAI(  # noqa: F841
            temperature=0,
            model_name=settings.model_name,
            openai_api_key=settings.openai_api_key,
        )
        # Implement web search logic
        return state

    def document_processor(state: AgentState) -> AgentState:
        """Processes and embeds documents for context."""
        # Implement document processing logic
        return state

    def response_generator(state: AgentState) -> AgentState:
        """Generates the final response based on collected information."""
        llm = ChatOpenAI(
            temperature=settings.temperature,
            model_name=settings.model_name,
            openai_api_key=settings.openai_api_key,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful assistant that generates responses based on collected information.",
                ),
                ("human", "{context}"),
            ]
        )
        chain = prompt | llm

        # Generate response using context
        response = chain.invoke({"context": str(state["context"])})

        # Update state
        state["messages"].append(SystemMessage(content=str(response)))
        state["current_step"] = "end"
        return state

    # Add nodes to the graph
    workflow.add_node("task_planner", task_planner)
    workflow.add_node("web_searcher", web_searcher)
    workflow.add_node("document_processor", document_processor)
    workflow.add_node("response_generator", response_generator)

    # Define conditional edges
    def should_web_search(state: AgentState) -> bool:
        return state["task_status"].get("needs_web_search", False)

    def should_process_documents(state: AgentState) -> bool:
        return state["task_status"].get("needs_document_processing", False)

    # Add edges with conditions
    workflow.add_conditional_edges(
        "task_planner",
        {
            "web_searcher": should_web_search,
            "document_processor": should_process_documents,
            "response_generator": lambda state: not (
                should_web_search(state) or should_process_documents(state)
            ),
        },
    )

    # Add edges from web searcher and document processor to response generator
    workflow.add_edge("web_searcher", "response_generator")
    workflow.add_edge("document_processor", "response_generator")

    # Set entry point
    workflow.set_entry_point("task_planner")

    # Compile the graph
    return workflow.compile()


def initialize_state(query: str) -> AgentState:
    """Initialize the agent state with a user query."""
    return AgentState(
        messages=[HumanMessage(content=query)],
        current_step="start",
        task_status={},
        context={},
    )
