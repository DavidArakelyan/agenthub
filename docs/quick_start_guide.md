# AgentHub Quick Start Guide

This guide provides the fastest way to get AgentHub up and running on your machine.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** installed (for cloning the repository)
- **OpenAI API Key** - [Get one here](https://platform.openai.com/api-keys)

## Check System Readiness (Recommended)

Before installation, we recommend running our system readiness check to ensure your environment is properly configured:

```bash
# After cloning the repository
cd agenthub
./check_system.sh
```

This will verify:
- Docker and Docker Compose installation
- Port availability
- System resources
- API key configuration

## Option 1: One-Line Installation (Recommended)

For the absolute fastest setup, use our one-line installer. This will clone the repository, set up the environment, start all services, and open the application in your browser.

```bash
curl -s https://raw.githubusercontent.com/yourusername/agenthub/main/quickstart.sh | bash -s -- your_openai_api_key
```

Replace `your_openai_api_key` with your actual OpenAI API key.

## Option 2: Using the Makefile

If you've already cloned the repository:

```bash
# Navigate to the project directory
cd agenthub

# Setup and start with one command (will prompt for API key if not set)
make quick-start

# Or provide API key directly
OPENAI_API_KEY=your_openai_api_key make quick-start
```

## Option 3: Manual Setup

If you prefer to run the commands manually:

```bash
# Clone the repository
git clone https://github.com/yourusername/agenthub.git
cd agenthub

# Quick setup with API key
./setup.sh quick your_openai_api_key

# Start the services
make start-local
```

## Verifying Installation

After running any of the above options, you should see Docker containers starting up. The application will be available at:

- **Frontend**: http://localhost:3000

To verify that all services are running correctly:

```bash
# Check running containers
docker ps

# Test the orchestrator API
curl http://localhost:8000/health
```

## What's Next?

1. **Create a new chat** by clicking the "+ New Chat" button
2. **Ask a question** or request the AI to generate content
3. **Explore the Canvas** where generated content appears
4. **Try uploading files** for the AI to analyze

## Stopping the Application

When you're done using AgentHub:

```bash
# Stop all services
make stop-local
```

## Troubleshooting

### Common Issues

1. **Docker containers won't start**
   - Ensure no other applications are using the required ports (3000, 8000, 8001, 8002)
   - Check if Docker is running with `docker info`

2. **API connection errors**
   - Wait a few moments for all services to initialize
   - Check container logs with `docker-compose -f deploy/docker/docker-compose.dev.yml logs`

3. **Invalid API key error**
   - Verify your OpenAI API key is correct and has available credits

For more detailed information, see:
- [Full Deployment Guide](deployment_guide.md)
- [User Guide](user_guide.md)
- [Technical Documentation](technical_documentation.md)
