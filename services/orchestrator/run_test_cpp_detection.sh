#!/bin/bash
# Run the C++ detection test script

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Set the path to the Python executable
PYTHON_EXEC="python"

# Check if a virtual environment exists
if [ -d ".venv_orchestrator" ]; then
    echo "Using Python from virtual environment .venv_orchestrator"
    PYTHON_EXEC=".venv_orchestrator/bin/python"
fi

# Make the test script executable
chmod +x test_cpp_detection.py

# Run the test script
$PYTHON_EXEC test_cpp_detection.py "$@"
