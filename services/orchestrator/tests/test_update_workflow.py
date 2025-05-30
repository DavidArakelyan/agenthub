"""Test script for the update query workflow.

This script tests the workflow's ability to handle update queries by:
1. Creating a sample content first
2. Then running an update query on that content
"""

import os
import sys
import logging
import time
import pytest
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store test results
test_results = None

from app.core.workflow import create_agent_workflow, initialize_state
from app.core.nodes.content_retriever import save_generated_content, retrieve_content
from app.core.types import QueryAction, GeneratorType, ComplexQuery, CodeLanguage


def test_code_update_workflow():
    """Test the code update workflow."""
    # First, let's generate a simple code
    original_query = "Create a Python function that calculates the factorial of a number"
    
    # Initialize workflow and state
    workflow = create_agent_workflow()
    state = initialize_state(original_query)
    
    # Set code generation parameters
    state["query"] = ComplexQuery(
        content=original_query,
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage.PYTHON,
        action=QueryAction.NEW
    )
    
    # Run the workflow
    logger.info("Running initial code generation workflow...")
    final_state = workflow.invoke(state)
    
    # Check if code was generated
    assert "canvas_content" in final_state["context"], "Code generation failed - no canvas content"
    code_content = final_state["context"]["canvas_content"]
    assert code_content, "Code content should not be empty"
    assert "def factorial" in code_content, "Generated code should include factorial function"
    
    # Save the generated code for later retrieval
    code_id = "factorial_function"
    metadata = {
        "generator_type": "code",
        "code_language": "py",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    save_generated_content(code_id, code_content, metadata)
    logger.info(f"Saved generated code with ID: {code_id}")
    
    # Wait a moment to ensure file is saved
    time.sleep(1)
    
    # Now, let's test updating the code
    update_query = f"Update the {code_id} to include better error handling"
    
    # Initialize new state for update
    update_state = initialize_state(update_query)
    
    # The workflow should automatically detect this as an update query,
    # retrieve the code, and update it
    
    # Run the workflow again
    logger.info("Running code update workflow...")
    update_final_state = workflow.invoke(update_state)
    
    # Check if update was successful
    assert "canvas_content" in update_final_state["context"], "Code update failed - no canvas content"
    updated_content = update_final_state["context"]["canvas_content"]
    assert updated_content, "Updated code content should not be empty"
    
    # Content should be different from original
    assert updated_content != code_content, "Updated content should be different from original"
    
    # Should include error handling
    assert "try:" in updated_content or "if " in updated_content and "raise" in updated_content, "Updated code should include error handling"
    
    logger.info("Code update workflow test passed!")
    # Store the content and updated content for the run_test function
    global test_results
    test_results = (code_content, updated_content)


def run_test():
    """Run the test and display results."""
    try:
        test_code_update_workflow()
        original, updated = test_results
        
        print("\n============ ORIGINAL CODE ============")
        print(original)
        
        print("\n============ UPDATED CODE ============")
        print(updated)
        
        print("\n============ TEST PASSED ============")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_test()
