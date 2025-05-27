#!/bin/bash
# Run the content extraction test script
cd "$(dirname "$0")"
echo "Starting content extraction test..."
python -u test_content_extraction.py
exit_code=$?
echo "Test completed with exit code: $exit_code"
exit $exit_code
