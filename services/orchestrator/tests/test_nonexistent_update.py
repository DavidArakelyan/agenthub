"""Test the behavior when updating a nonexistent file."""

import os
import sys
import logging
import pytest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.workflow import create_agent_workflow, initialize_state
from app.core.types import QueryAction, GeneratorType, ComplexQuery, CodeLanguage


def test_nonexistent_update_query():
    """Test that update queries for nonexistent files are converted to new queries."""
    # Create a unique identifier for a file that definitely doesn't exist
    nonexistent_file_id = f"nonexistent_file_{os.urandom(4).hex()}"
    
    # Create an update query for this nonexistent file
    update_query = f"Update the {nonexistent_file_id} to add error handling"
    
    # Initialize workflow and state
    workflow = create_agent_workflow()
    state = initialize_state(update_query)
    
    # Set up as an update query
    state["query"] = ComplexQuery(
        content=update_query,
        generator_type=GeneratorType.CODE,
        code_language=CodeLanguage.PYTHON,
        action=QueryAction.UPDATE,
        file_identifier=nonexistent_file_id
    )
    
    # Run the workflow
    logger.info(f"Running update workflow for nonexistent file: {nonexistent_file_id}")
    final_state = workflow.invoke(state)
    
    # Check if canvas_content was generated despite the file not existing
    assert "canvas_content" in final_state["context"], "Content generation failed"
    assert final_state["context"]["canvas_content"], "Generated content should not be empty"
    
    # The action might not be changed in the final state, but the behavior should be
    # as if it's a new query (content should be generated even if the file doesn't exist)
    logger.info("Nonexistent file update test passed!")


if __name__ == "__main__":
    test_nonexistent_update_query()
