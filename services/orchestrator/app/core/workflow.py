"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Any, Dict, List, Union
from langgraph.graph import Graph, StateGraph
from langchain.schema import BaseMessage
from langchain_core.messages import HumanMessage, SystemMessage
import logging

from app.core.config import get_settings
from app.core.types import SimpleQuery, ComplexQuery, GeneratorType
from app.core.types import AgentState
from app.core.nodes import (
    query_type_classifier,
    generator_type_classifier,
    language_classifier,
    format_classifier,
    web_searcher,
    document_processor,
    code_generator,
    document_generator,
    response_generator,
)

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentWorkflow:
    """Workflow implementation using LangGraph."""

    def __init__(self):
        """Initialize the workflow."""
        self.workflow = create_agent_workflow()

    async def ainvoke(self, state):
        """Invoke the workflow asynchronously."""
        try:
            logger.info(f"Processing state: {state}")
            # Execute the workflow
            result = await self.workflow.ainvoke(state)
            logger.info(f"Workflow completed with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            return {
                "context": {
                    "code_generation_completed": False,
                    "document_generation_completed": False,
                    "error": str(e),
                }
            }


def create_agent_workflow() -> Graph:
    """Creates the main agent workflow using LangGraph."""
    logger.info("Creating the main agent workflow using LangGraph...\n")
    try:
        workflow = StateGraph(AgentState)

        def query_type_router_func(s):
            if isinstance((s["query"]), ComplexQuery):
                return "generator_type_classifier"
            return "response_generator"

        def generation_type_router_func(s):
            if s["query"].generator_type == GeneratorType.CODE:
                return "language_classifier"
            elif s["query"].generator_type == GeneratorType.DOCUMENT:
                return "format_classifier"
            return "response_generator"

        # Add nodes
        workflow.add_node("query_type_classifier", query_type_classifier)
        workflow.add_node("generator_type_classifier", generator_type_classifier)
        workflow.add_node("language_classifier", language_classifier)
        workflow.add_node("format_classifier", format_classifier)
        workflow.add_node("web_searcher", web_searcher)
        workflow.add_node("document_processor", document_processor)
        workflow.add_node("code_generator", code_generator)
        workflow.add_node("document_generator", document_generator)
        workflow.add_node("response_generator", response_generator)

        # Add conditional edges
        workflow.add_conditional_edges("query_type_classifier", query_type_router_func)
        workflow.add_conditional_edges(
            "generator_type_classifier", generation_type_router_func
        )
        # Add explicit edges to corresponding generators
        workflow.add_edge("language_classifier", "code_generator")
        workflow.add_edge("format_classifier", "document_generator")
        # Direct edges to response generator
        workflow.add_edge("code_generator", "response_generator")
        workflow.add_edge("document_generator", "response_generator")

        # Set entry point
        workflow.set_entry_point("query_type_classifier")
        graph = workflow.compile()

        return graph

    except Exception as e:
        logger.error(f"Error creating agent workflow: {str(e)}")
        raise


def initialize_state(query: str) -> AgentState:
    """Initialize the agent state with a user query."""
    try:
        logger.info(f"Initializing agent state with query: {query}")
        state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "current_step": "start",
            "task_status": {},  # Empty dict to be populated by query classifier
            "context": {
                "code_generation_completed": False,
                "document_generation_completed": False,
                "web_search_completed": False,
                "document_processed": False,
                "error": None,
            },
            "query": SimpleQuery(content=query),  # Default to simple query
        }
        logger.info("Successfully initialized agent state")
        return state
    except Exception as e:
        logger.error(f"Error initializing agent state: {str(e)}")
        raise
