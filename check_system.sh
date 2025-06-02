#!/bin/bash
# AgentHub System Readiness Check
# This script checks if your system meets all requirements for running AgentHub

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_section() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker
check_docker() {
    print_section "Docker"
    
    if command_exists docker; then
        print_success "Docker is installed"
        
        # Check Docker version
        docker_version=$(docker --version | cut -d ' ' -f3 | cut -d ',' -f1)
        print_info "Docker version: $docker_version"
        
        # Check if Docker daemon is running
        if docker info >/dev/null 2>&1; then
            print_success "Docker daemon is running"
        else
            print_error "Docker daemon is not running"
            print_info "Try running: 'sudo systemctl start docker' (Linux) or start Docker Desktop (Mac/Windows)"
            return 1
        fi
    else
        print_error "Docker is not installed"
        print_info "Visit https://docs.docker.com/get-docker/ for installation instructions"
        return 1
    fi
    
    return 0
}

# Check Docker Compose
check_docker_compose() {
    print_section "Docker Compose"
    
    if command_exists docker-compose; then
        print_success "Docker Compose is installed"
        
        # Check Docker Compose version
        compose_version=$(docker-compose --version | cut -d ' ' -f3)
        print_info "Docker Compose version: $compose_version"
    else
        # Check if Docker Compose plugin is available
        if docker compose version >/dev/null 2>&1; then
            print_success "Docker Compose plugin is installed"
            print_info "Using Docker Compose plugin"
        else
            print_error "Docker Compose is not installed"
            print_info "Visit https://docs.docker.com/compose/install/ for installation instructions"
            return 1
        fi
    fi
    
    return 0
}

# Check ports
check_ports() {
    print_section "Port Availability"
    
    # Check if port is in use
    port_in_use() {
        if command_exists lsof; then
            lsof -i:$1 >/dev/null 2>&1
            return $?
        elif command_exists netstat; then
            netstat -tuln | grep -q ":$1 "
            return $?
        else
            # If neither lsof nor netstat is available, assume port is free
            return 1
        fi
    }
    
    # List of required ports
    ports=(3000 8000 8001 8002 6379 5672 15672 19530 9091 9090 3001)
    
    for port in "${ports[@]}"; do
        if port_in_use $port; then
            print_error "Port $port is already in use"
            print_info "You need to free this port before proceeding"
        else
            print_success "Port $port is available"
        fi
    done
}

# Check system resources
check_resources() {
    print_section "System Resources"
    
    # Check total memory
    if command_exists free; then
        # Linux
        total_mem=$(free -m | awk '/^Mem:/{print $2}')
        free_mem=$(free -m | awk '/^Mem:/{print $4}')
    elif command_exists vm_stat && command_exists sysctl; then
        # macOS
        page_size=$(vm_stat | grep "page size" | cut -d ' ' -f 8)
        total_mem=$(sysctl -n hw.memsize | awk -v page_size=$page_size '{print int($1/1024/1024)}')
        free_pages=$(vm_stat | grep "Pages free" | awk '{print int($3)}')
        free_mem=$(echo "$free_pages * $page_size / 1024 / 1024" | bc)
    else
        total_mem="unknown"
        free_mem="unknown"
    fi
    
    if [ "$total_mem" != "unknown" ]; then
        print_info "Total memory: ${total_mem}MB"
        if [ $total_mem -lt 4000 ]; then
            print_warning "Less than 4GB RAM detected. AgentHub may run slowly."
        else
            print_success "Memory is sufficient"
        fi
        
        if [ "$free_mem" != "unknown" ]; then
            print_info "Free memory: ${free_mem}MB"
            if [ $free_mem -lt 2000 ]; then
                print_warning "Less than 2GB free RAM. Consider closing other applications."
            else
                print_success "Free memory is sufficient"
            fi
        fi
    fi
    
    # Check disk space
    if command_exists df; then
        free_space_kb=$(df -k . | awk 'NR==2 {print $4}')
        free_space_gb=$(echo "scale=2; $free_space_kb/1024/1024" | bc)
        print_info "Free disk space: ${free_space_gb}GB"
        
        if (( $(echo "$free_space_gb < 5" | bc -l) )); then
            print_warning "Less than 5GB free disk space. This might not be enough."
        else
            print_success "Disk space is sufficient"
        fi
    fi
}

# Check for OpenAI API key
check_api_key() {
    print_section "OpenAI API Key"
    
    if [ -n "$OPENAI_API_KEY" ]; then
        # Mask the API key for display
        masked_key="${OPENAI_API_KEY:0:3}...${OPENAI_API_KEY: -4}"
        print_success "OpenAI API key is set: $masked_key"
        
        # Basic format validation
        if [[ $OPENAI_API_KEY == sk-* ]]; then
            print_success "API key format appears valid"
        else
            print_warning "API key format looks unusual (should start with 'sk-')"
        fi
    else
        print_warning "OpenAI API key is not set in environment"
        print_info "You will need to provide an API key during setup"
    fi
}

# Check Git
check_git() {
    print_section "Git"
    
    if command_exists git; then
        print_success "Git is installed"
        git_version=$(git --version | cut -d ' ' -f3)
        print_info "Git version: $git_version"
    else
        print_warning "Git is not installed"
        print_info "Git is recommended for cloning the repository"
    fi
}

# Main function
main() {
    echo "🔍 AgentHub System Readiness Check"
    echo "=================================="
    echo "Checking if your system is ready to run AgentHub..."
    
    # Run all checks
    docker_ok=true
    compose_ok=true
    
    check_docker || docker_ok=false
    check_docker_compose || compose_ok=false
    
    # Only continue with other checks if Docker is working
    if [ "$docker_ok" = true ] && [ "$compose_ok" = true ]; then
        check_ports
        check_resources
        check_git
        check_api_key
        
        echo ""
        print_success "Basic system checks completed"
        echo ""
        print_info "If any warnings or errors were shown, you may want to address them before proceeding."
        print_info "To proceed with installation, run: ./setup.sh"
    else
        echo ""
        print_error "Critical requirements are not met. Please fix the issues above before proceeding."
    fi
}

# Execute main function
main
