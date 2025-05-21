"""Tests for workflow components."""

import pytest
from app.core.workflow_v2 import create_agent_workflow, initialize_state, AgentState
from langchain.schema import HumanMessage
import logging
import sys

# Configure logging to show all logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # This ensures logs go to the Debug Console
    ],
)

# Set log level for specific loggers
logging.getLogger("app.core.workflow").setLevel(logging.DEBUG)
logging.getLogger("langchain").setLevel(logging.INFO)


def test_initialize_state():
    """Test state initialization."""
    query = "Generate a Python function to sort a list"
    state = initialize_state(query)

    assert isinstance(state, AgentState)
    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], HumanMessage)
    assert state["messages"][0].content == query
    assert state["current_step"] == "start"
    assert state["query_type"] == "simple"
    assert state["generation_type"] == "none"
    assert state["target_format"] == "none"


def test_create_workflow():
    """Test workflow creation."""
    workflow = create_agent_workflow()
    assert workflow is not None


@pytest.mark.parametrize(
    "query,expected_type,expected_gen,expected_format",
    [
        ("Write a Python function to sort a list", "complex", "code", "py"),
        ("Create documentation for API endpoints", "complex", "document", "doc"),
        ("What is the capital of France?", "simple", "none", "none"),
    ],
)
async def test_query_classification(
    query, expected_type, expected_gen, expected_format
):
    """Test query classification with different inputs."""
    workflow = create_agent_workflow()
    state = initialize_state(query)

    # Run the workflow
    result = await workflow.ainvoke(state)

    assert result["query_type"] == expected_type
    assert result["generation_type"] == expected_gen
    assert result["target_format"] == expected_format


@pytest.mark.parametrize(
    "query,should_search",
    [
        ("What are the latest trends in AI?", True),
        ("What is 2+2?", False),
    ],
)
async def test_web_search_condition(query, should_search):
    """Test web search conditional execution."""
    workflow = create_agent_workflow()
    state = initialize_state(query)

    # Run the workflow
    result = await workflow.ainvoke(state)

    assert result["task_status"].get("needs_web_search", False) == should_search
