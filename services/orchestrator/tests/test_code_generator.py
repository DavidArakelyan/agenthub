"""Tests for code generation functionality."""

import pytest
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: F401
import logging
import sys

from app.core.workflow import initialize_state, AgentWorkflow
from app.core.types import GeneratorType, CodeLanguage, ComplexQuery, DocumentFormat

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

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    "language,query",
    [
        ("py", "Write a function to calculate factorial"),
        ("cpp", "Create a class for managing a stack"),
        ("java", "Implement a binary search tree"),
        ("ts", "Create a React component with TypeScript interfaces"),
    ],
)
async def test_code_generation(language, query):
    """Test code generation for different languages."""
    state = initialize_state(query)
    # Add debug logging
    print(f"\nInitial state: {state}\n")

    state["query"] = ComplexQuery(
        content=query,
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage(language),
    )
    print(f"State after query setup: {state}\n")

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)
    print(f"Workflow result: {result}\n")

    # Verify results
    assert result["context"]["code_generation_completed"] is True
    assert result["context"].get("error") is None
    assert "generated_code" in result["context"]
    assert isinstance(result["messages"][-1], SystemMessage)

    # TypeScript-specific assertions
    if language == "ts":
        code = result["context"]["generated_code"]
        assert "interface" in code.lower() or "type" in code.lower()
        assert "React" in code
        assert ": " in code  # Type annotations
        assert "export" in code.lower()


@pytest.mark.parametrize(
    "language,query",
    [
        ("py", "Create a complex web scraper with async support and error handling"),
        ("cpp", "Implement a thread-safe singleton pattern with RAII"),
        ("java", "Create a generic REST client with retry mechanism"),
        ("ts", "Build a React app with hooks and context API"),
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


@pytest.mark.parametrize(
    "format,query",
    [
        ("txt", "Write documentation about API endpoints"),
        ("md", "Create a README with installation instructions"),  # Add Markdown test
        ("doc", "Generate a technical specification document"),
        ("pdf", "Create a project proposal"),
    ],
)
async def test_document_generation(format, query):
    """Test document generation for different formats."""
    state = initialize_state(query)
    state["query"] = ComplexQuery(
        content=query,
        generator_type=GeneratorType.DOCUMENT,
        document_format=DocumentFormat(format),
    )

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)

    assert result["context"]["document_generation_completed"] is True
    assert result["context"].get("error") is None
    assert "generated_document" in result["context"]

    # Markdown-specific assertions
    if format == "md":
        doc = result["context"]["generated_document"]
        assert "#" in doc  # Headers
        assert "```" in doc  # Code blocks
        assert "- " in doc or "* " in doc  # Lists
        assert "[" in doc and "](" in doc  # Links


@pytest.mark.parametrize(
    "language,invalid_code",
    [
        ("ts", "function test(x) { return x + 1; }"),  # Missing type annotation
        ("ts", "var x = 5;"),  # Using var instead of let/const
        ("ts", "const Component = () => <div>Hello</div>"),  # Missing type/interface
    ],
)
async def test_typescript_validation(language, invalid_code):
    """Test TypeScript code validation rules."""
    state = initialize_state("Generate TypeScript code")
    state["query"] = ComplexQuery(
        content=invalid_code,
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage(language),
    )

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)

    # Verify that the generated code follows TypeScript best practices
    generated_code = result["context"]["generated_code"]
    assert "let" in generated_code or "const" in generated_code
    assert ": " in generated_code  # Type annotations
    assert "interface" in generated_code.lower() or "type" in generated_code.lower()


@pytest.mark.parametrize(
    "format,invalid_markdown",
    [
        ("md", "#Invalid Header"),  # No space after #
        ("md", "|Column1|Column2|\n|Content1|Content2|"),  # Missing header separator
        ("md", "[Invalid Link]()"),  # Empty link target
    ],
)
async def test_markdown_validation(format, invalid_markdown):
    """Test Markdown syntax validation rules."""
    state = initialize_state("Generate Markdown document")
    state["query"] = ComplexQuery(
        content=invalid_markdown,
        generator_type=GeneratorType.DOCUMENT,
        document_format=DocumentFormat(format),
    )

    workflow = AgentWorkflow()
    result = await workflow.ainvoke(state)

    # Verify that the generated markdown follows proper syntax
    generated_doc = result["context"]["generated_document"]
    assert "# " in generated_doc  # Proper header syntax
    if "|" in generated_doc:  # Table validation
        table_lines = [line for line in generated_doc.split("\n") if "|" in line]
        assert len(table_lines) >= 3  # Header, separator, and content
        assert "|-" in generated_doc  # Proper separator
    if "[" in generated_doc:  # Link validation
        assert "](" in generated_doc and ")" in generated_doc
        assert "]()" not in generated_doc  # No empty links


@pytest.fixture
async def cleanup_generated_files(tmp_path):
    """Fixture to clean up any files created during tests."""
    yield
    # Clean up any generated files here if needed
    for file in tmp_path.glob("*"):
        file.unlink()
