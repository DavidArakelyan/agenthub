#!/bin/bash
# AgentHub Quick Start Script
# Usage: curl -s https://raw.githubusercontent.com/yourusername/agenthub/main/quickstart.sh | bash -s -- your_openai_api_key

set -e

if [ -z "$1" ]; then
  echo "Error: OpenAI API key is required"
  echo "Usage: curl -s https://raw.githubusercontent.com/yourusername/agenthub/main/quickstart.sh | bash -s -- your_openai_api_key"
  exit 1
fi

OPENAI_API_KEY=$1

echo "🚀 AgentHub Quick Start"
echo "⏳ Cloning repository..."
git clone https://github.com/yourusername/agenthub.git
cd agenthub

echo "⏳ Setting up environment..."
export OPENAI_API_KEY=$OPENAI_API_KEY
./setup.sh quick $OPENAI_API_KEY

echo "⏳ Starting services..."
make start-local

echo "✅ AgentHub is now running!"
echo "📱 Open http://localhost:3000 in your browser"

# Try to open the browser automatically
if command -v open >/dev/null 2>&1; then
  open http://localhost:3000
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:3000
elif command -v start >/dev/null 2>&1; then
  start http://localhost:3000
fi

echo "❓ To stop the application, run: make stop-local"
