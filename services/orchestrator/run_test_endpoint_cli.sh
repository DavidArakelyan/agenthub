#!/bin/bash
# Run the CLI test tool for orchestrator service

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment if it exists
if [ -d "$DIR/.venv_orchestrator" ]; then
  source "$DIR/.venv_orchestrator/bin/activate"
fi

# Install tabulate if it's not already installed
pip show tabulate >/dev/null 2>&1 || pip install tabulate

# Run the CLI tool
python -m tests.test_orchestrator_cli "$@"

# Deactivate virtual environment if we activated it
if [ -d "$DIR/.venv_orchestrator" ]; then
  deactivate 2>/dev/null || true
fi
