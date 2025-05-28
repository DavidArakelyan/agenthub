"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Dict
from langgraph.graph import Graph, StateGraph
from langchain_core.messages import HumanMessage
import logging

from app.core.config import get_settings
from app.core.types import SimpleQuery, ComplexQuery, GeneratorType
from app.core.types import AgentState
from app.core.nodes.web_searcher import web_searcher
from app.core.nodes.document_processor import document_processor
from app.core.nodes.code_generator import code_generator
from app.core.nodes.document_generator import document_generator
from app.core.nodes import (
    query_type_classifier,
    generator_type_classifier,
    language_classifier,
    format_classifier,
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

    def invoke(self, state):
        """Invoke the workflow synchronously."""
        try:
            logger.info(f"Processing state synchronously: {state}")
            # Execute the workflow synchronously
            result = self.workflow.invoke(state)
            logger.info(f"Synchronous workflow completed with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in synchronous workflow execution: {str(e)}")
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


async def run_workflow_async(state: AgentState) -> Dict:
    """Run the workflow asynchronously."""
    try:
        logger.info("Running workflow asynchronously...")
        workflow = AgentWorkflow()
        result = await workflow.ainvoke(state)
        return result
    except Exception as e:
        logger.error(f"Error running workflow asynchronously: {str(e)}")
        raise


def run_workflow(state: AgentState) -> Dict:
    """Run the workflow synchronously by wrapping the async implementation."""
    import asyncio

    try:
        logger.info("Running workflow synchronously (via async wrapper)...")

        # Get-or-Create Pattern for event loop
        try:
            loop = asyncio.get_event_loop()
            should_close_loop = False
        except RuntimeError:
            # Create a new loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            should_close_loop = True

        try:
            # Run the async workflow function
            result = loop.run_until_complete(run_workflow_async(state))
            return result
        finally:
            # Only close the loop if we created it
            if should_close_loop:
                loop.close()

    except Exception as e:
        logger.error(f"Error running workflow synchronously: {str(e)}")
        raise
