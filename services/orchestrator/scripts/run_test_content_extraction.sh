#!/bin/bash
# Run the content extraction test script
cd "$(dirname "$0")/.."
echo "Starting content extraction test..."
python -u -m tests.test_content_extraction
exit_code=$?
echo "Test completed with exit code: $exit_code"
exit $exit_code
