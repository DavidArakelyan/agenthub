#!/bin/bash

# Add the service directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the workflow CLI
python test_workflow_cli.py
