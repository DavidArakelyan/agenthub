#!/bin/bash
# This script demonstrates how to debug your FastAPI application in VS Code

echo "====================== DEBUGGING GUIDE ======================"
echo "To properly debug your FastAPI application with breakpoints:"
echo ""
echo "Option 1: Using VS Code's debugger"
echo "  1. Open VS Code"
echo "  2. Go to Run and Debug (Ctrl+Shift+D / Cmd+Shift+D)"
echo "  3. Select 'Python: FastAPI (No Reload)' from the dropdown"
echo "  4. Press F5 to start debugging"
echo "  5. When you hit a line with debug_break(), execution will pause"
echo ""
echo "Option 2: Manual running and attaching"
echo "  1. Run this script (./debug_guide.sh) in one terminal"
echo "  2. In VS Code, select 'Python: FastAPI Backend (Attach)' and press F5"
echo ""
echo "====================== STARTING SERVER ======================"
echo "Starting server without reload for proper debugging..."

# Run the service
cd "$(dirname "$0")"
# No --reload flag means Uvicorn won't auto-reload on file changes
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
