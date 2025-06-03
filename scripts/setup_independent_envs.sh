#!/bin/bash
# Script to set up independent virtual environments for each service

# Set error handling
set -e

# Function to log messages
log() {
  echo "$(date +'%Y-%m-%d %H:%M:%S') - $1"
}

# Array of service directories
services=("orchestrator" "documents" "websearch")

log "Creating independent virtual environments for each service..."

for service in "${services[@]}"; do
  log "Setting up virtual environment for $service service..."
  
  # Navigate to service directory
  cd "services/$service" || { log "Error: Could not find service directory: $service"; exit 1; }
  
  # Check if service-specific virtual environment already exists
  if [ -d ".venv_${service}" ]; then
    log "Virtual environment .venv_${service} already exists for $service..."
    log "Updating existing environment..."
  else
    # Create service-specific virtual environment
    log "Creating new virtual environment .venv_${service} for $service..."
    python -m venv ".venv_${service}"
  fi
  
  # Activate and install dependencies
  source ".venv_${service}/bin/activate"
  
  # Upgrade pip and install development tools
  log "Upgrading pip and installing dependencies for $service..."
  pip install --upgrade pip
  
  # Install from locked requirements if available, otherwise from requirements.txt
  if [ -f "requirements-lock.txt" ]; then
    log "Installing from locked requirements for $service..."
    pip install -r requirements-lock.txt
  else
    log "Installing from requirements.txt for $service..."
    pip install -r requirements.txt
  fi
  
  # Install the package in development mode if setup.py exists
  if [ -f "setup.py" ]; then
    log "Installing package in development mode for $service..."
    pip install -e .
  fi
  
  # Create activation helper script for this service
  cat > "activate_${service}.sh" << EOF
#!/bin/bash
# Helper script to activate the virtual environment for $service
source .venv_${service}/bin/activate
export PYTHONPATH=\${PYTHONPATH}:\$(pwd)
echo "✅ Virtual environment activated for $service service"
echo "✅ Run 'deactivate' to exit the virtual environment"
EOF
  chmod +x "activate_${service}.sh"
  
  # Deactivate virtual environment
  deactivate
  
  # Go back to project root
  cd ../..
  
  log "✅ Virtual environment set up for $service service"
done

# Set up frontend dependencies
log "Setting up frontend dependencies..."
cd "services/frontend" || { log "Error: Could not find frontend directory"; exit 1; }

# Install frontend dependencies
npm ci --prefer-offline

# Create run helper script
cat > "start_frontend.sh" << EOF
#!/bin/bash
# Helper script to start frontend in development mode
export REACT_APP_API_BASE_URL=http://localhost:8000
export REACT_APP_WS_URL=ws://localhost:8000/ws
export REACT_APP_DOCUMENT_SERVICE_URL=http://localhost:8001
export REACT_APP_WEBSEARCH_SERVICE_URL=http://localhost:8002
npm start
EOF
chmod +x start_frontend.sh

cd ../..

log "✅ All service virtual environments have been created successfully!"
log ""
log "To activate a service's virtual environment, run:"
log "  source services/SERVICE_NAME/activate_SERVICE_NAME.sh"
log ""
log "To start a service independently:"
log "  1. Activate its virtual environment"
log "  2. Run the appropriate start command:"
log "     - Orchestrator: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
log "     - Documents: uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
log "     - Web Search: uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"
log "     - Frontend: ./start_frontend.sh"
