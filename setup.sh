#!/bin/bash
# AgentHub Setup Script
# This script sets up the AgentHub application for development or production

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${BLUE}[AgentHub Setup]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[AgentHub Setup]${NC} $1"
}

print_error() {
    echo -e "${RED}[AgentHub Setup]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_message "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        print_message "Visit https://docs.docker.com/get-docker/ for installation instructions."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        print_message "Visit https://docs.docker.com/compose/install/ for installation instructions."
        exit 1
    fi
    
    # Check Git (optional)
    if ! command_exists git; then
        print_message "Git is not installed. It's recommended but not required."
    fi
    
    # Check Python (required for virtual environments)
    if ! command_exists python; then
        print_error "Python is not installed. Python is required for setting up virtual environments."
        exit 1
    fi
    
    # Check pip-tools for requirements-lock.txt generation
    if ! command_exists pip-compile; then
        print_message "pip-tools is not installed. Installing..."
        pip install pip-tools
        print_success "pip-tools installed successfully."
    fi
    
    print_success "All essential prerequisites are installed."
}

# Initialize OpenAI API Key 
initialize_api_key() {
    print_message "Setting up API key..."
    
    # Check if .env file exists and contains OPENAI_API_KEY
    if [ -f .env ] && grep -q "OPENAI_API_KEY" .env; then
        # Extract the API key from .env file
        openai_key=$(grep "OPENAI_API_KEY" .env | cut -d '=' -f2)
        print_message "Using OpenAI API key from .env file."
    elif [ -n "$OPENAI_API_KEY" ]; then
        # Use the API key from environment variable
        openai_key=$OPENAI_API_KEY
        print_message "Using OpenAI API key from environment variable."
    elif [ -n "$1" ]; then
        # Use the API key provided as argument
        openai_key=$1
        print_message "Using OpenAI API key provided as argument."
    else
        # Prompt for API key
        read -p "Enter your OpenAI API key: " openai_key
    fi
    
    # Export it for the setup_independent_envs.sh script to use
    export OPENAI_API_KEY=$openai_key
    
    # Create or update .env file with the API key
    if [ ! -f .env ]; then
        echo "OPENAI_API_KEY=$openai_key" > .env
        echo "ENVIRONMENT=development" >> .env
        print_success "Created .env file with API key."
    elif ! grep -q "OPENAI_API_KEY" .env; then
        echo "OPENAI_API_KEY=$openai_key" >> .env
        print_success "Added API key to .env file."
    fi
}

# Generate requirements-lock.txt files for each service
generate_lock_files() {
    print_message "Checking for requirements-lock.txt files..."
    
    # Array of service directories with Python requirements
    services=("orchestrator" "documents" "websearch")
    
    for service in "${services[@]}"; do
        if [ -f "services/$service/requirements.txt" ]; then
            if [ ! -f "services/$service/requirements-lock.txt" ] || [ "services/$service/requirements.txt" -nt "services/$service/requirements-lock.txt" ]; then
                print_message "Generating requirements-lock.txt for $service service..."
                (cd "services/$service" && pip-compile requirements.txt -o requirements-lock.txt)
                print_success "Generated requirements-lock.txt for $service service."
            else
                print_message "requirements-lock.txt for $service service is up to date."
            fi
        fi
    done
}



# Setup development environment
setup_dev() {
    print_message "Setting up development environment..."
    
    # Initialize API key
    initialize_api_key "$1"
    
    # Create required directories
    mkdir -p deploy/prometheus
    
    # Generate requirements-lock.txt files for each service
    generate_lock_files
    
    # Set up individual service environments
    print_message "Setting up independent virtual environments for each service..."
    if [ -f scripts/setup_independent_envs.sh ]; then
        chmod +x scripts/setup_independent_envs.sh
        # Run the script to create environments
        ./scripts/setup_independent_envs.sh
        print_success "Virtual environments created successfully."
    else
        print_error "setup_independent_envs.sh script not found!"
        exit 1
    fi
    
    # Install global dependencies (if needed)
    if command_exists python3; then
        print_message "Installing global Python dependencies..."
        python3 -m pip install --upgrade pip
        if [ -f requirements-dev.txt ]; then
            python3 -m pip install -r requirements-dev.txt
        fi
    fi
    
    # Pull Docker images for all services
    print_message "Pulling Docker images for all services..."
    docker-compose -f deploy/docker/docker-compose.dev.yml --profile all pull
    
    # Create helper script for development deployment
    print_message "Creating helper scripts for deployment..."
    cat > start-dev.sh << 'EOL'
#!/bin/bash
# Helper script to start development environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Starting development environment..."

# Default profile is 'all'
PROFILE="all"

# If argument is provided, use it as the profile
if [ -n "$1" ]; then
  PROFILE="$1"
  echo -e "${BLUE}[AgentHub]${NC} Using profile: $PROFILE"
else
  echo -e "${BLUE}[AgentHub]${NC} Using default profile: all"
fi

# Start the services with the specified profile
docker-compose -f deploy/docker/docker-compose.dev.yml --profile "$PROFILE" up -d

echo -e "${GREEN}[AgentHub]${NC} Development environment started!"
echo -e "${BLUE}[AgentHub]${NC} Access the application at http://localhost:3000"
echo -e "${BLUE}[AgentHub]${NC} To stop the environment: ./stop-dev.sh $PROFILE"
EOL
    chmod +x start-dev.sh
    
    # Create stop script for development environment
    cat > stop-dev.sh << 'EOL'
#!/bin/bash
# Helper script to stop development environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Stopping development environment..."

# Default profile is 'all'
PROFILE="all"

# If argument is provided, use it as the profile
if [ -n "$1" ]; then
  PROFILE="$1"
  echo -e "${BLUE}[AgentHub]${NC} Using profile: $PROFILE"
else
  echo -e "${BLUE}[AgentHub]${NC} Using default profile: all"
fi

# Stop the services with the specified profile
docker-compose -f deploy/docker/docker-compose.dev.yml --profile "$PROFILE" down

echo -e "${GREEN}[AgentHub]${NC} Development environment stopped!"
EOL
    chmod +x stop-dev.sh
    
    print_success "Development environment setup complete!"
    
    print_message "To start all services with Docker: ./start-dev.sh"
    print_message "To start only supporting services: ./start-dev.sh support"
    print_message "To start each service independently:"
    print_message "  1. Activate a service environment with: source services/SERVICE_NAME/activate_SERVICE_NAME.sh"
    print_message "  2. Run the service with the appropriate command from the activation script output"
}

# Setup production environment
setup_prod() {
    print_message "Setting up production environment..."
    
    # Initialize API key
    initialize_api_key
    
    # Create required directories
    mkdir -p deploy/prometheus
    mkdir -p deploy/docker/nginx/ssl
    
    # Generate requirements-lock.txt files for each service
    generate_lock_files
    
    # Generate self-signed SSL certificate for testing
    if [ ! -f deploy/docker/nginx/ssl/cert.pem ]; then
        print_message "Generating self-signed SSL certificate for testing..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout deploy/docker/nginx/ssl/key.pem \
            -out deploy/docker/nginx/ssl/cert.pem \
            -subj "/CN=agenthub.yourdomain.com"
        print_success "Generated self-signed SSL certificate."
    fi
    
    # Build Docker images
    print_message "Building Docker images..."
    docker-compose -f deploy/docker/docker-compose.prod.yml build
    
    # Create helper script for production deployment
    print_message "Creating helper script for production deployment..."
    cat > start-prod.sh << 'EOL'
#!/bin/bash
# Helper script to start production environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Starting production environment..."

# Start the services
docker-compose -f deploy/docker/docker-compose.prod.yml up -d

echo -e "${GREEN}[AgentHub]${NC} Production environment started!"
echo -e "${BLUE}[AgentHub]${NC} Access the application at https://your-domain"
echo -e "${BLUE}[AgentHub]${NC} To stop the environment: ./stop-prod.sh"
EOL
    chmod +x start-prod.sh

    # Create stop script for production environment
    cat > stop-prod.sh << 'EOL'
#!/bin/bash
# Helper script to stop production environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Stopping production environment..."

# Stop the services
docker-compose -f deploy/docker/docker-compose.prod.yml down

echo -e "${GREEN}[AgentHub]${NC} Production environment stopped!"
EOL
    chmod +x stop-prod.sh
    
    print_success "Production environment setup complete!"
    print_message "To start the production environment, run: ./start-prod.sh"
}



# Main function
main() {
    print_message "Welcome to AgentHub Setup!"
    
    # Check prerequisites
    check_prerequisites
    
    # Determine setup type
    local setup_type="dev"
    local api_key=""
    
    if [ "$1" == "production" ]; then
        setup_type="production"
    elif [ "$1" == "quick" ]; then
        setup_type="quick"
        api_key="$2"
    else
        # Default to dev
        setup_type="dev"
        api_key="$1"
    fi
    
    # Check if python is required for virtual environments
    if ! command_exists python; then
        print_error "Python is not installed. Python is required for setting up virtual environments."
        exit 1
    fi
    
    # Run the selected setup
    if [ "$setup_type" == "production" ]; then
        setup_prod
    elif [ "$setup_type" == "quick" ]; then
        print_message "Running quick setup..."
        initialize_api_key "$api_key"
        
        # Generate requirements-lock.txt files
        generate_lock_files
        
        if [ -f scripts/setup_independent_envs.sh ]; then
            chmod +x scripts/setup_independent_envs.sh
            ./scripts/setup_independent_envs.sh
        else
            print_error "setup_independent_envs.sh script not found!"
            exit 1
        fi
        
        # Create helper script for development deployment
        print_message "Creating helper script for deployment..."
        cat > start-dev.sh << 'EOL'
#!/bin/bash
# Helper script to start development environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Starting development environment..."

# Default profile is 'all'
PROFILE="all"

# If argument is provided, use it as the profile
if [ -n "$1" ]; then
  PROFILE="$1"
  echo -e "${BLUE}[AgentHub]${NC} Using profile: $PROFILE"
else
  echo -e "${BLUE}[AgentHub]${NC} Using default profile: all"
fi

# Start the services with the specified profile
docker-compose -f deploy/docker/docker-compose.dev.yml --profile "$PROFILE" up -d

echo -e "${GREEN}[AgentHub]${NC} Development environment started!"
echo -e "${BLUE}[AgentHub]${NC} Access the application at http://localhost:3000"
echo -e "${BLUE}[AgentHub]${NC} To stop the environment: ./stop-dev.sh $PROFILE"
EOL
        chmod +x start-dev.sh
        
        # Create stop script for development environment
        cat > stop-dev.sh << 'EOL'
#!/bin/bash
# Helper script to stop development environment

# Set error handling
set -e

# Define color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${BLUE}[AgentHub]${NC} Stopping development environment..."

# Default profile is 'all'
PROFILE="all"

# If argument is provided, use it as the profile
if [ -n "$1" ]; then
  PROFILE="$1"
  echo -e "${BLUE}[AgentHub]${NC} Using profile: $PROFILE"
else
  echo -e "${BLUE}[AgentHub]${NC} Using default profile: all"
fi

# Stop the services with the specified profile
docker-compose -f deploy/docker/docker-compose.dev.yml --profile "$PROFILE" down

echo -e "${GREEN}[AgentHub]${NC} Development environment stopped!"
EOL
        chmod +x stop-dev.sh
        
        print_message "Quick setup completed. Run './start-dev.sh' to start all services or './start-dev.sh support' for support services only."
        exit 0
    else
        setup_dev "$api_key"
    fi
    
    print_success "Setup completed successfully."
    echo ""
    print_message "You can now start the application with one of the following commands:"
    
    if [ "$setup_type" == "production" ]; then
        print_message "  • Production: ./start-prod.sh"
    else
        print_message "  • All services with Docker: ./start-dev.sh"
        print_message "  • Support services only: ./start-dev.sh support"
        print_message ""
        print_message "  • To run services manually in separate terminals:"
        print_message "    • Orchestrator: source services/orchestrator/activate_orchestrator.sh && cd services/orchestrator && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        print_message "    • Documents: source services/documents/activate_documents.sh && cd services/documents && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload"
        print_message "    • Web Search: source services/websearch/activate_websearch.sh && cd services/websearch && uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"
        print_message "    • Frontend: cd services/frontend && ./start_frontend.sh"
    fi
    
    echo ""
    if [ "$setup_type" == "dev" ]; then
        print_message "Access the application at http://localhost:3000 after starting all services"
    else
        print_message "Access the application at https://your-domain"
    fi
}

# Parse command line arguments
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: ./setup.sh [options] [api_key]"
    echo ""
    echo "Options:"
    echo "  dev          Setup development environment with Docker and independent environments (default)"
    echo "  production   Setup production environment"
    echo "  quick        Setup with environments only (requires API key as second argument or OPENAI_API_KEY env var)"
    echo "  -h, --help   Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                          # Standard dev setup with prompts"
    echo "  ./setup.sh dev sk-abcd1234          # Dev setup with API key provided"
    echo "  ./setup.sh quick sk-abcd1234        # Quick setup with API key provided"
    echo "  OPENAI_API_KEY=sk-abcd1234 ./setup.sh quick  # Quick setup using env var"
    echo ""
    echo "Development setup:"
    echo "  - Creates independent virtual environments for each service via setup_independent_envs.sh"
    echo "  - Generates requirements-lock.txt files for all services if needed"
    echo "  - Pulls Docker images for ALL services"
    echo "  - Creates helper scripts (start-dev.sh, start-prod.sh) for easier deployment"
    echo "  - Run './start-dev.sh [profile]' to start services (default profile: all)"
    exit 0
fi

# Execute main function
main "$1" "$2"
