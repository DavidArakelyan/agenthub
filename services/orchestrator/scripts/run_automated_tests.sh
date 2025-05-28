#!/bin/bash
# Run automated tests against the orchestrator service

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$DIR")"

# Check if the orchestrator service is running
if ! curl -s http://localhost:8000/health >/dev/null; then
  echo "⚠️  Orchestrator service is not running. Starting it..."
  
  # Start the service in the background
  "$DIR/run_orchestrator_no_reload.sh" &
  SERVICE_PID=$!
  
  # Wait for service to start
  echo "Waiting for service to start..."
  for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null; then
      echo "✅ Service is up and running!"
      break
    fi
    
    if [ $i -eq 10 ]; then
      echo "❌ Service failed to start within the timeout period."
      kill $SERVICE_PID 2>/dev/null
      exit 1
    fi
    
    echo "Waiting... ($i/10)"
    sleep 2
  done
  
  # Give it an extra second just to be safe
  sleep 1
fi

# Run the automated tests
echo "Running automated tests..."
"$PARENT_DIR/run_test_endpoint_cli.sh" --test

# Store the exit code
EXIT_CODE=$?

# If we started the service, stop it
if [ -n "$SERVICE_PID" ]; then
  echo "Stopping orchestrator service..."
  kill $SERVICE_PID 2>/dev/null
fi

# Exit with the test script's exit code
exit $EXIT_CODE
