"""Tests for code generation component."""

import pytest
from app.core.workflow import (
    initialize_state,
    code_generator,
)


@pytest.mark.parametrize(
    "language,query",
    [
        ("py", "Write a function to calculate factorial"),
        ("cpp", "Create a class for managing a stack"),
        ("java", "Implement a binary search tree"),
    ],
)
def test_code_generation(language, query):
    """Test code generation for different languages."""
    # Initialize state with test data
    state = initialize_state(query)
    state["target_format"] = language
    state["generation_type"] = "code"

    # Run code generator
    result = code_generator(state)

    # Verify results
    assert result["context"]["code_generation_completed"] is True
    assert "generated_code" in result["context"]
    assert result["context"]["error"] is None if "error" in result["context"] else True

    # Verify language-specific markers in generated code
    code = result["context"]["generated_code"]
    if language == "py":
        assert "def " in code or "class " in code
    elif language == "cpp":
        assert "#include" in code or "class " in code
    elif language == "java":
        assert "public class" in code or "public interface" in code


def test_code_generator_error_handling():
    """Test error handling in code generation."""
    # Initialize state with invalid language
    state = initialize_state("Write some code")
    state["target_format"] = "invalid_language"
    state["generation_type"] = "code"

    # Run code generator
    result = code_generator(state)

    # Verify error handling
    assert result["context"]["code_generation_completed"] is False
    assert "error" in result["context"]
