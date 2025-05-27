#!/usr/bin/env python
"""
Test script for the code and document generators.
This script tests the extraction of pure code and documents.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

# Import the relevant modules
from app.core.types import (
    AgentState,
    ComplexQuery,
    CodeLanguage,
    GeneratorType,
    DocumentFormat,
)
from app.core.nodes.code_generator import code_generator
from app.core.nodes.document_generator import document_generator
from app.core.nodes.response_generator import response_generator
from app.core.config import get_settings
from langchain_core.messages import HumanMessage


async def test_code_generator():
    """Test the code generator to ensure it extracts pure code."""
    print("\n=== Testing Code Generator ===")

    # Create a test query
    query = ComplexQuery(
        content="Write a Python function to calculate fibonacci numbers",
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage.PYTHON,
        document_format=None,
    )

    # Create initial state
    state = AgentState(
        messages=[HumanMessage(content=query.content)],
        current_step="code_generator",
        context={},
        query=query,
        task_status={},
    )

    # Run the code generator
    try:
        result_state = await code_generator(state)

        # Display the results
        print("\nGenerated Code (Raw):")
        print("-" * 50)
        print(
            result_state["context"].get("generated_code_raw", "")[:500] + "..."
            if len(result_state["context"].get("generated_code_raw", "")) > 500
            else result_state["context"].get("generated_code_raw", "")
        )

        print("\nExtracted Pure Code:")
        print("-" * 50)
        print(result_state["context"].get("generated_code", ""))

        if (
            "code_explanation" in result_state["context"]
            and result_state["context"]["code_explanation"]
        ):
            print("\nCode Explanation:")
            print("-" * 50)
            print(result_state["context"].get("code_explanation", ""))

        # Set canvas_content using response_generator logic
        result_state = response_generator(result_state)

        print("\nCanvas Content (for saving):")
        print("-" * 50)
        print(result_state["context"].get("canvas_content", ""))

        return result_state
    except Exception as e:
        print(f"Error testing code generator: {e}")
        return None


async def test_document_generator():
    """Test the document generator to ensure it extracts pure documents."""
    print("\n=== Testing Document Generator ===")

    # Create a test query
    query = ComplexQuery(
        content="Write a markdown tutorial about Python decorators",
        generator_type=GeneratorType.DOCUMENT,
        code_language=None,
        document_format=DocumentFormat.MARKDOWN,
    )

    # Create initial state
    state = AgentState(
        messages=[HumanMessage(content=query.content)],
        current_step="document_generator",
        context={},
        query=query,
        task_status={},
    )

    # Run the document generator
    try:
        result_state = await document_generator(state)

        # Display the results
        print("\nGenerated Document (Raw):")
        print("-" * 50)
        print(
            result_state["context"].get("generated_document_raw", "")[:500] + "..."
            if len(result_state["context"].get("generated_document_raw", "")) > 500
            else result_state["context"].get("generated_document_raw", "")
        )

        print("\nExtracted Pure Document:")
        print("-" * 50)
        print(
            result_state["context"].get("generated_document", "")[:500] + "..."
            if len(result_state["context"].get("generated_document", "")) > 500
            else result_state["context"].get("generated_document", "")
        )

        if (
            "document_explanation" in result_state["context"]
            and result_state["context"]["document_explanation"]
        ):
            print("\nDocument Explanation:")
            print("-" * 50)
            print(result_state["context"].get("document_explanation", ""))

        # Set canvas_content using response_generator logic
        result_state = response_generator(result_state)

        print("\nCanvas Content (for saving):")
        print("-" * 50)
        print(
            result_state["context"].get("canvas_content", "")[:500] + "..."
            if len(result_state["context"].get("canvas_content", "")) > 500
            else result_state["context"].get("canvas_content", "")
        )

        return result_state
    except Exception as e:
        print(f"Error testing document generator: {e}")
        return None


async def main():
    """Run the tests."""
    print("Testing Pure Content Extraction")

    # Test code generator
    code_state = await test_code_generator()

    # Test document generator
    doc_state = await test_document_generator()

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
