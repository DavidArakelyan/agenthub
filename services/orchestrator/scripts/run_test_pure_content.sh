#!/bin/bash
# Run test for pure content extraction
cd "$(dirname "$0")/.."
echo "Starting pure content extraction test..."
python -m tests.test_pure_content
