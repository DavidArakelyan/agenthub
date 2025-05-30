#!/bin/bash
# Run the content retriever and update workflow tests

# Change to the project root directory
cd "$(dirname "$0")/.."

# Run pytest with the new test files
python -m pytest tests/test_content_retriever.py tests/test_document_update_workflow.py tests/test_update_workflow.py -v
