#!/bin/bash
# Debug the orchestrator service without auto-reload

cd "$(dirname "$0")"
# Run without the reload flag (default is no reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
