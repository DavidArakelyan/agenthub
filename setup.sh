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
    
    print_success "All essential prerequisites are installed."
}

# Create environment files
create_env_files() {
    print_message "Creating environment files..."
    
    # Root .env file
    if [ ! -f .env ]; then
        if [ -n "$OPENAI_API_KEY" ]; then
            # Use the API key from environment variable
            openai_key=$OPENAI_API_KEY
            print_message "Using OpenAI API key from environment variable."
        elif [ -n "$2" ]; then
            # Use the API key provided as argument
            openai_key=$2
            print_message "Using OpenAI API key provided as argument."
        else
            # Prompt for API key
            read -p "Enter your OpenAI API key: " openai_key
        fi
        
        echo "OPENAI_API_KEY=$openai_key" > .env
        echo "ENVIRONMENT=development" >> .env
        print_success "Created .env file."
    else
        print_message ".env file already exists."
    fi
    
    # Frontend .env file
    if [ ! -f services/frontend/.env ]; then
        mkdir -p services/frontend
        cat > services/frontend/.env << EOL
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_DOCUMENT_SERVICE_URL=http://localhost:8001
REACT_APP_WEBSEARCH_SERVICE_URL=http://localhost:8002
REACT_APP_MAX_FILE_SIZE=10485760
EOL
        print_success "Created frontend .env file."
    else
        print_message "Frontend .env file already exists."
    fi
    
    if [ "$1" == "production" ]; then
        # Production .env file
        if [ ! -f .env.prod ]; then
            cp .env .env.prod
            sed -i "" "s/ENVIRONMENT=development/ENVIRONMENT=production/g" .env.prod
            print_success "Created .env.prod file."
        else
            print_message ".env.prod file already exists."
        fi
    fi
}

# Setup development environment
setup_dev() {
    print_message "Setting up development environment..."
    
    # Create environment files
    create_env_files "development" "$1"
    
    # Create required directories
    mkdir -p deploy/prometheus
    
    # Install dependencies
    if command_exists python3; then
        print_message "Installing Python dependencies..."
        python3 -m pip install --upgrade pip
        if [ -f requirements-dev.txt ]; then
            python3 -m pip install -r requirements-dev.txt
        fi
    fi
    
    if command_exists npm; then
        print_message "Installing Node.js dependencies..."
        if [ -d services/frontend ]; then
            (cd services/frontend && npm install)
        fi
    fi
    
    # Pull Docker images
    print_message "Pulling Docker images..."
    docker-compose -f deploy/docker/docker-compose.dev.yml pull
    
    print_success "Development environment setup complete!"
    print_message "To start the development environment, run: make start-local"
}

# Setup production environment
setup_prod() {
    print_message "Setting up production environment..."
    
    # Create environment files
    create_env_files "production"
    
    # Create required directories
    mkdir -p deploy/prometheus
    mkdir -p deploy/docker/nginx/ssl
    
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
    
    print_success "Production environment setup complete!"
    print_message "To start the production environment, run: docker-compose -f deploy/docker/docker-compose.prod.yml up -d"
}

# Main function
main() {
    print_message "Welcome to AgentHub Setup!"
    
    # Check prerequisites
    check_prerequisites
    
    # Determine setup type
    if [ "$1" == "production" ]; then
        setup_prod
    elif [ "$1" == "quick" ]; then
        print_message "Running quick setup..."
        create_env_files "development" "$2"
        print_message "Quick setup completed. Run 'make start-local' to start the application."
        exit 0
    else
        setup_dev "$2"
    fi
    
    print_success "Setup completed successfully."
    echo ""
    print_message "You can now start the application with one of the following commands:"
    print_message "  • Development: make start-local"
    print_message "  • Production: docker-compose -f deploy/docker/docker-compose.prod.yml up -d"
    echo ""
    print_message "Access the application at http://localhost:3000 (dev) or https://your-domain (prod)"
}

# Parse command line arguments
if [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: ./setup.sh [options] [api_key]"
    echo ""
    echo "Options:"
    echo "  dev        Setup development environment (default)"
    echo "  production Setup production environment"
    echo "  quick      Minimal setup for quick start (requires API key as second argument or OPENAI_API_KEY env var)"
    echo "  -h, --help Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                          # Standard dev setup with prompts"
    echo "  ./setup.sh dev sk-abcd1234          # Dev setup with API key provided"
    echo "  ./setup.sh quick sk-abcd1234        # Quick setup with API key provided"
    echo "  OPENAI_API_KEY=sk-abcd1234 ./setup.sh quick  # Quick setup using env var"
    exit 0
fi

# Execute main function
main "$1" "$2"
