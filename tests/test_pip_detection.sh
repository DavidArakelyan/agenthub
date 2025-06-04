#!/bin/bash

# Simple test script
echo "Testing pip command detection:"

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi
echo "Detected Python command: $PYTHON_CMD"

if command -v pip &>/dev/null; then
    PIP_CMD="pip"
elif command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
else
    echo "ERROR: No pip command found!"
    exit 1
fi
echo "Detected pip command: $PIP_CMD"

# Test calling pip with the PIP_CMD
echo "Testing pip version:"
$PIP_CMD --version

echo "All tests passed!"
