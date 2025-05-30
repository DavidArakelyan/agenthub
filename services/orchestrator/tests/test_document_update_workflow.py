"""Test script for the document update query workflow.

This script tests the workflow's ability to handle document update queries by:
1. Creating a sample document first
2. Then running an update query on that document
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
from app.core.types import QueryAction, GeneratorType, ComplexQuery, DocumentFormat


def test_document_update_workflow():
    """Test the document update workflow."""
    # First, let's generate a simple document
    original_query = "Create a markdown document about the benefits of AI"
    
    # Initialize workflow and state
    workflow = create_agent_workflow()
    state = initialize_state(original_query)
    
    # Set document generation parameters
    state["query"] = ComplexQuery(
        content=original_query,
        generator_type=GeneratorType.DOCUMENT,
        document_format=DocumentFormat.MARKDOWN,
        action=QueryAction.NEW
    )
    
    # Run the workflow
    logger.info("Running initial document generation workflow...")
    final_state = workflow.invoke(state)
    
    # Check if document was generated
    assert "canvas_content" in final_state["context"], "Document generation failed - no canvas content"
    document_content = final_state["context"]["canvas_content"]
    assert document_content, "Document content should not be empty"
    
    # Save the generated document for later retrieval
    document_id = "ai_benefits_doc"
    metadata = {
        "generator_type": "document",
        "document_format": "md",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    save_generated_content(document_id, document_content, metadata)
    logger.info(f"Saved generated document with ID: {document_id}")
    
    # Wait a moment to ensure file is saved
    time.sleep(1)
    
    # Now, let's test updating the document
    update_query = f"Update the {document_id} document to include a section on ethical considerations"
    
    # Initialize new state for update
    update_state = initialize_state(update_query)
    
    # The workflow should automatically detect this as an update query,
    # retrieve the document, and update it
    
    # Run the workflow again
    logger.info("Running document update workflow...")
    update_final_state = workflow.invoke(update_state)
    
    # Check if update was successful
    assert "canvas_content" in update_final_state["context"], "Document update failed - no canvas content"
    updated_content = update_final_state["context"]["canvas_content"]
    assert updated_content, "Updated document content should not be empty"
    
    # Content should be different from original
    assert updated_content != document_content, "Updated content should be different from original"
    
    # Should include keywords from both original and update query
    # Check for various ways the benefits of AI might be mentioned
    assert any(phrase in updated_content.lower() for phrase in ["benefits of ai", "ai benefits", "artificial intelligence"]), "Updated content should retain original topic"
    assert "ethical considerations" in updated_content.lower(), "Updated content should include new topic"
    
    logger.info("Document update workflow test passed!")
    # Store the content and updated content for the run_test function
    global test_results
    test_results = (document_content, updated_content)


def run_test():
    """Run the test and display results."""
    try:
        test_document_update_workflow()
        original, updated = test_results
        
        print("\n============ ORIGINAL DOCUMENT ============")
        print(original[:500] + "..." if len(original) > 500 else original)
        
        print("\n============ UPDATED DOCUMENT ============")
        print(updated[:500] + "..." if len(updated) > 500 else updated)
        
        print("\n============ TEST PASSED ============")
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise


if __name__ == "__main__":
    run_test()
