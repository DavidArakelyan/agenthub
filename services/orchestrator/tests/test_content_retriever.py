"""Test script for content retriever functionality.

This script tests if the content retriever can access and read files from the 
existing generated_content directory.
"""

import os
import sys
import logging
import pytest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.nodes.content_retriever import (
    CONTENT_STORE_PATH,
    ensure_store_exists,
    save_generated_content,
    retrieve_content,
)


def test_content_store_path_exists():
    """Test if the content store path is set correctly and exists."""
    ensure_store_exists()
    assert os.path.exists(CONTENT_STORE_PATH), f"Content store path {CONTENT_STORE_PATH} does not exist"
    logger.info(f"Content store path exists at: {CONTENT_STORE_PATH}")


def test_save_and_retrieve_content():
    """Test saving and retrieving content."""
    # Generate a unique file ID
    file_id = f"test_content_{os.urandom(4).hex()}"
    test_content = "This is test content for retrieval test."
    test_metadata = {"generator_type": "code", "code_language": "py"}
    
    # Save the content
    save_generated_content(file_id, test_content, test_metadata)
    
    # Retrieve the content
    retrieved_data = retrieve_content(file_id)
    
    # Verify the content was retrieved correctly
    assert retrieved_data is not None, "Retrieved data should not be None"
    assert "content" in retrieved_data, "Retrieved data should have content field"
    assert "metadata" in retrieved_data, "Retrieved data should have metadata field"
    assert retrieved_data["content"] == test_content, "Retrieved content does not match"
    assert retrieved_data["metadata"]["generator_type"] == test_metadata["generator_type"], "Retrieved metadata does not match"
    assert retrieved_data["metadata"]["code_language"] == test_metadata["code_language"], "Retrieved metadata does not match"
    
    logger.info(f"Successfully saved and retrieved content with ID: {file_id}")


def test_retrieve_nonexistent_content():
    """Test retrieving content that doesn't exist."""
    nonexistent_id = f"nonexistent_{os.urandom(4).hex()}"
    retrieved_data = retrieve_content(nonexistent_id)
    
    # Should return an empty dict with content and metadata keys
    assert "content" in retrieved_data, "Retrieved data should have content field even for nonexistent files"
    assert "metadata" in retrieved_data, "Retrieved data should have metadata field even for nonexistent files"
    assert retrieved_data["content"] == "", "Content should be empty for nonexistent files"
    
    logger.info("Successfully handled nonexistent content retrieval")


def test_retrieve_fuzzy_match():
    """Test retrieving content with fuzzy matching."""
    # Generate a unique file ID
    file_id = f"fuzzy_match_test_{os.urandom(4).hex()}"
    test_content = "This is test content for fuzzy matching test."
    test_metadata = {"generator_type": "document", "document_format": "md"}
    
    # Save the content
    save_generated_content(file_id, test_content, test_metadata)
    
    # Try to retrieve with a slightly modified ID
    fuzzy_id = file_id.replace("_test_", "_test")  # Remove one underscore
    retrieved_data = retrieve_content(fuzzy_id)
    
    # Verify the content was retrieved correctly despite the fuzzy match
    assert retrieved_data is not None, "Retrieved data should not be None"
    assert "content" in retrieved_data, "Retrieved data should have content field"
    assert retrieved_data["content"] == test_content, "Retrieved content does not match with fuzzy search"
    
    logger.info(f"Successfully retrieved content with fuzzy match: {fuzzy_id} -> {file_id}")


def run_tests():
    """Run all tests manually."""
    logger.info("Running content retriever tests...")
    test_content_store_path_exists()
    test_save_and_retrieve_content()
    test_retrieve_nonexistent_content()
    test_retrieve_fuzzy_match()
    logger.info("All content retriever tests passed!")


if __name__ == "__main__":
    run_tests()
