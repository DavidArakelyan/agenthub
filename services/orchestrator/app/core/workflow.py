"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Annotated, Any, Dict, List, TypedDict, Literal  # noqa: F401
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
    query_type: Literal["simple", "complex"]
    generation_type: Literal["code", "document", "none"]
    target_format: str


def create_agent_workflow() -> Graph:
    """
    Creates the main agent workflow using LangGraph.

    The workflow implements the Model Context Protocol and handles:
    1. Query Classification
    2. Task Planning
    3. Web Search (conditional)
    4. Document Processing (conditional)
    5. Code Generation (conditional)
    6. Document Generation (conditional)
    7. Response Generation
    """
    # Initialize the state graph
    workflow = StateGraph(AgentState)

    # Define the nodes (agents)
    def query_classifier(state: AgentState) -> AgentState:
        """Classifies the query as simple or complex and determines required processing."""
        llm = ChatOpenAI(
            temperature=0,
            model_name=settings.model_name,
            openai_api_key=settings.openai_api_key,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a query classification agent. Analyze the query and determine:\n"
                    "1. If it's a simple query (within LLM's knowledge, no code/doc generation, no context)\n"
                    "2. If it's a complex query (needs recent info, code/doc generation, or has context)\n"
                    "3. If it requires code generation (specify language: cpp, py, java)\n"
                    "4. If it requires document generation (specify format: txt, doc, pdf)\n"
                    "Return a JSON with the following structure:\n"
                    "{\n"
                    '  "query_type": "simple" | "complex",\n'
                    '  "needs_web_search": boolean,\n'
                    '  "needs_document_processing": boolean,\n'
                    '  "generation_type": "code" | "document" | "none",\n'
                    '  "target_format": "cpp" | "py" | "java" | "txt" | "doc" | "pdf" | "none"\n'
                    "}",
                ),
                ("human", "{input}"),
            ]
        )
        chain = prompt | llm

        # Get the query from state
        query = state["messages"][-1].content

        # Classify query and parse the response
        classification = chain.invoke({"input": query})
        try:
            class_data = json.loads(classification.content)
            state["query_type"] = class_data.get("query_type", "simple")
            state["task_status"]["needs_web_search"] = class_data.get(
                "needs_web_search", False
            )
            state["task_status"]["needs_document_processing"] = class_data.get(
                "needs_document_processing", False
            )
            state["generation_type"] = class_data.get("generation_type", "none")
            state["target_format"] = class_data.get("target_format", "none")
        except json.JSONDecodeError:
            # Default to simple query if parsing fails
            state["query_type"] = "simple"
            state["task_status"]["needs_web_search"] = False
            state["task_status"]["needs_document_processing"] = False
            state["generation_type"] = "none"
            state["target_format"] = "none"

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

    def code_generator(state: AgentState) -> AgentState:
        """Generates code in the specified programming language."""
        # Use a specialized LLM for code generation
        llm = ChatOpenAI(  # noqa: F841
            temperature=0.2,  # Lower temperature for more deterministic code generation
            model_name="gpt-4",  # Using GPT-4 for better code generation
            openai_api_key=settings.openai_api_key,
        )
        # Implement code generation logic
        return state

    def document_generator(state: AgentState) -> AgentState:
        """Generates documents in the specified format."""
        # Use a specialized LLM for document generation
        llm = ChatOpenAI(  # noqa: F841
            temperature=0.7,
            model_name="gpt-4",  # Using GPT-4 for better document generation
            openai_api_key=settings.openai_api_key,
        )
        # Implement document generation logic
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
    workflow.add_node("query_classifier", query_classifier)
    workflow.add_node("web_searcher", web_searcher)
    workflow.add_node("document_processor", document_processor)
    workflow.add_node("code_generator", code_generator)
    workflow.add_node("document_generator", document_generator)
    workflow.add_node("response_generator", response_generator)

    # Define conditional edges
    def should_web_search(state: AgentState) -> bool:
        return state["task_status"].get("needs_web_search", False)

    def should_process_documents(state: AgentState) -> bool:
        return state["task_status"].get("needs_document_processing", False)

    def should_generate_code(state: AgentState) -> bool:
        return state["generation_type"] == "code"

    def should_generate_document(state: AgentState) -> bool:
        return state["generation_type"] == "document"

    def is_simple_query(state: AgentState) -> bool:
        return state["query_type"] == "simple"

    # Add edges with conditions
    workflow.add_conditional_edges(
        "query_classifier",
        {
            "web_searcher": should_web_search,
            "document_processor": should_process_documents,
            "code_generator": should_generate_code,
            "document_generator": should_generate_document,
            "response_generator": lambda state: (
                is_simple_query(state)
                or not any(
                    [
                        should_web_search(state),
                        should_process_documents(state),
                        should_generate_code(state),
                        should_generate_document(state),
                    ]
                )
            ),
        },
    )

    # Add edges from all processors to response generator
    workflow.add_edge("web_searcher", "response_generator")
    workflow.add_edge("document_processor", "response_generator")
    workflow.add_edge("code_generator", "response_generator")
    workflow.add_edge("document_generator", "response_generator")

    # Set entry point
    workflow.set_entry_point("query_classifier")

    # Compile the graph
    return workflow.compile()


def initialize_state(query: str) -> AgentState:
    """Initialize the agent state with a user query."""
    return AgentState(
        messages=[HumanMessage(content=query)],
        current_step="start",
        task_status={},
        context={},
        query_type="simple",
        generation_type="none",
        target_format="none",
    )
