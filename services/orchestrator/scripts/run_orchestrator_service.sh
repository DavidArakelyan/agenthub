#!/bin/bash

# Add the service directory to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Run the FastAPI application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
