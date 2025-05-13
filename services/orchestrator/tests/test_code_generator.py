"""Tests for code generation functionality."""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: F401
from app.core.workflow import (
    initialize_state,
    AgentWorkflow,
    GeneratorType,
    CodeLanguage,
    ComplexQuery,
)

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "language,query",
    [
        ("py", "Write a function to calculate factorial"),
        ("cpp", "Create a class for managing a stack"),
        ("java", "Implement a binary search tree"),
    ],
)
async def test_code_generation(language, query):
    """Test code generation for different languages."""
    state = initialize_state(query)
    # Add debug logging
    print(f"\nInitial state: {state}")

    state["query"] = ComplexQuery(
        content=query,
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage(language),
    )
    print(f"State after query setup: {state}")

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)
    print(f"Workflow result: {result}")

    # Verify results
    assert result["context"]["code_generation_completed"] is True
    assert result["context"].get("error") is None
    assert "generated_code" in result["context"]
    assert isinstance(result["messages"][-1], SystemMessage)


@pytest.mark.parametrize(
    "language,query",
    [
        ("py", "Create a complex web scraper with async support and error handling"),
        ("cpp", "Implement a thread-safe singleton pattern with RAII"),
        ("java", "Create a generic REST client with retry mechanism"),
    ],
)
async def test_complex_code_generation(language, query):
    """Test code generation for complex scenarios."""
    state = initialize_state(query)
    state["target_format"] = language
    state["generation_type"] = "code"
    state["query_type"] = "complex"  # Mark as complex query

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)

    assert result["context"]["code_generation_completed"] is True
    assert "generated_code" in result["context"]
    assert result["context"]["error"] is None

    code = result["context"]["generated_code"]

    # Verify complex features based on language
    if language == "py":
        assert "async" in code  # Check for async support
        assert "try:" in code  # Check for error handling
        assert "except" in code
        assert "class" in code  # Should be class-based
    elif language == "cpp":
        assert "std::mutex" in code or "std::lock_guard" in code  # Thread safety
        assert "static" in code  # Singleton pattern
        assert "delete" in code  # RAII cleanup
    elif language == "java":
        assert "implements" in code or "extends" in code  # Check inheritance/interfaces
        assert "<" in code and ">" in code  # Check for generics
        assert "try" in code and "catch" in code  # Error handling


async def test_code_generator_error_handling():
    """Test error handling in code generation."""
    # Test with invalid language
    state = initialize_state("Write some code")
    state["target_format"] = "invalid_language"
    state["generation_type"] = "code"

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)
    print(f"Result context: {result['context']}")  # Debug print

    assert result["context"]["code_generation_completed"] is False
    assert "error" in result["context"]
    assert "invalid_language" in str(result["context"]["error"]).lower()

    # Test with empty query
    state = initialize_state("")
    state["target_format"] = "py"
    state["generation_type"] = "code"

    result = await workflow.ainvoke(state)

    assert result["context"]["code_generation_completed"] is False
    assert "error" in result["context"]
    assert "empty" in str(result["context"]["error"]).lower()


@pytest.fixture
async def cleanup_generated_files(tmp_path):
    """Fixture to clean up any files created during tests."""
    yield
    # Clean up any generated files here if needed
    for file in tmp_path.glob("*"):
        file.unlink()
