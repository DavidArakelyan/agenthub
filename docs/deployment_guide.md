# AgentHub Deployment Guide

This guide provides detailed instructions for setting up and deploying the AgentHub platform in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Setup](#quick-setup)
3. [Development Setup](#development-setup)
4. [Production Deployment](#production-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Container Management](#container-management)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (20.10.x or later)
- **Docker Compose** (2.x or later)
- **Git** (2.x or later)
- **Node.js** (16.x or later) - for local frontend development
- **Python** (3.9 or later) - for local backend development
- **OpenAI API Key** - for language model access

## Quick Setup

This section provides the fastest way to get AgentHub up and running after cloning the repository.

### One-Line Installation

For the absolute fastest setup, you can use our one-line installer (replace `your_openai_api_key` with your actual API key):

```bash
curl -s https://raw.githubusercontent.com/yourusername/agenthub/main/quickstart.sh | bash -s -- your_openai_api_key
```

This command will:
1. Clone the repository
2. Set up the environment with your API key
3. Start all services
4. Open the application in your browser

### Using Makefile

If you've already cloned the repository, you can use the Makefile for a quick setup:

```bash
# Navigate to the project directory
cd agenthub

# Setup and start with one command (will prompt for API key if not set)
make quick-start

# Or provide API key directly
OPENAI_API_KEY=your_openai_api_key make quick-start
```

### Manual Quick Setup

If you prefer to run the commands manually:

```bash
# Clone the repository
git clone https://github.com/yourusername/agenthub.git
cd agenthub

# Set your OpenAI API key (replace with your actual key)
export OPENAI_API_KEY=your_openai_api_key_here

# Run the automated setup script and start the application
./setup.sh quick $OPENAI_API_KEY && make start-local
```

After running these commands, the application will be available at:
- Frontend: http://localhost:3000

### Verify Installation

To verify that all services are running correctly:

```bash
# Check the status of all containers
docker ps

# Test the orchestrator service
curl http://localhost:8000/health

# Open the web interface
open http://localhost:3000
```

### Stopping the Application

When you're done, you can stop all services with:

```bash
make stop-local
```

### Common Issues with Quick Setup

- If you see "permission denied" when running setup.sh, run `chmod +x setup.sh` first
- If any service fails to start, check the logs with `docker-compose -f deploy/docker/docker-compose.dev.yml logs`
- If you need to restart a specific service, use `docker-compose -f deploy/docker/docker-compose.dev.yml restart [service_name]`

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/agenthub.git
cd agenthub
```

### 2. Create Environment Files

Create a root `.env` file:

```bash
cat > .env << EOL
OPENAI_API_KEY=your_openai_api_key
ENVIRONMENT=development
EOL
```

Create a frontend `.env` file:

```bash
cat > services/frontend/.env << EOL
REACT_APP_API_BASE_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_DOCUMENT_SERVICE_URL=http://localhost:8001
REACT_APP_WEBSEARCH_SERVICE_URL=http://localhost:8002
REACT_APP_MAX_FILE_SIZE=10485760
EOL
```

### 3. Build and Start the Development Environment

Use the Makefile for convenience:

```bash
# Setup the development environment
make setup-dev

# Start all services
make start-local
```

Alternatively, use Docker Compose directly:

```bash
docker-compose -f deploy/docker/docker-compose.dev.yml build
docker-compose -f deploy/docker/docker-compose.dev.yml up -d
```

### 4. Accessing the Services

- **Frontend**: http://localhost:3000
- **Orchestrator API**: http://localhost:8000
- **Document Service**: http://localhost:8001
- **Web Search Service**: http://localhost:8002
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)

### 5. Local Development

For frontend development:

```bash
cd services/frontend
npm install
npm start
```

For backend service development:

```bash
cd services/[service_name]
python -m pip install -r requirements.txt
python -m app.main
```

## Production Deployment

### 1. Create Production Docker Compose File

Create a new file at `deploy/docker/docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  orchestrator:
    build:
      context: ../../services/orchestrator
      dockerfile: Dockerfile
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - ../../.env.prod
    environment:
      - ENVIRONMENT=production
    volumes:
      - orchestrator_data:/app/data
    depends_on:
      - redis
      - rabbitmq

  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data

  rabbitmq:
    image: rabbitmq:3-management-alpine
    restart: always
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  milvus:
    image: milvusdb/milvus:v2.3.1
    restart: always
    volumes:
      - milvus_data:/var/lib/milvus
    environment:
      - ETCD_CFG.auto-compaction-mode=revision
      - ETCD_CFG.auto-compaction-retention=1000
      - COMMON_CFG.retention_duration=100

  websearch:
    build:
      context: ../../services/websearch
      dockerfile: Dockerfile
    restart: always
    env_file:
      - ../../.env.prod

  frontend:
    build:
      context: ../../services/frontend
      dockerfile: Dockerfile
    restart: always
    ports:
      - "80:3000"
    environment:
      - REACT_APP_API_BASE_URL=/api
      - REACT_APP_WS_URL=/api/ws
      - REACT_APP_DOCUMENT_SERVICE_URL=/document
      - REACT_APP_WEBSEARCH_SERVICE_URL=/websearch
      - REACT_APP_MAX_FILE_SIZE=10485760
  
  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - orchestrator
      - websearch

volumes:
  redis_data:
  rabbitmq_data:
  milvus_data:
  orchestrator_data:
```

### 2. Create Nginx Configuration

Create nginx configuration directory and file:

```bash
mkdir -p deploy/docker/nginx
cat > deploy/docker/nginx/nginx.conf << EOL
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;
    keepalive_timeout 65;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    server {
        listen 443 ssl;
        server_name agenthub.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        
        # Frontend
        location / {
            proxy_pass http://frontend:3000;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }

        # Orchestrator API
        location /api/ {
            proxy_pass http://orchestrator:8000/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            
            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade \$http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Document Service
        location /document/ {
            proxy_pass http://documents:8001/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            client_max_body_size 20M;
        }

        # Web Search Service
        location /websearch/ {
            proxy_pass http://websearch:8002/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
        }
    }
}
EOL
```

### 3. Create Production Environment File

```bash
cat > .env.prod << EOL
OPENAI_API_KEY=your_openai_api_key
ENVIRONMENT=production
LOG_LEVEL=INFO
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
MILVUS_HOST=milvus
MILVUS_PORT=19530
EOL
```

### 4. Deploy to Production

```bash
# Build all services
docker-compose -f deploy/docker/docker-compose.prod.yml build

# Start in production mode
docker-compose -f deploy/docker/docker-compose.prod.yml up -d
```

## Environment Configuration

### Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ENVIRONMENT` | Environment (development/production) | development |
| `LOG_LEVEL` | Logging level | INFO |
| `REDIS_URL` | Redis connection URL | redis://redis:6379/0 |
| `RABBITMQ_URL` | RabbitMQ connection URL | amqp://guest:guest@rabbitmq:5672/ |
| `MILVUS_HOST` | Milvus host | milvus |
| `MILVUS_PORT` | Milvus port | 19530 |

### Frontend Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REACT_APP_API_BASE_URL` | Orchestrator API URL | http://localhost:8000 |
| `REACT_APP_WS_URL` | WebSocket URL | ws://localhost:8000/ws |
| `REACT_APP_DOCUMENT_SERVICE_URL` | Document service URL | http://localhost:8001 |
| `REACT_APP_WEBSEARCH_SERVICE_URL` | Web search service URL | http://localhost:8002 |
| `REACT_APP_MAX_FILE_SIZE` | Maximum file size in bytes | 10485760 (10MB) |

## Container Management

See [Docker Quick Guide](../docs/docker-quickguide.md) for common Docker commands and best practices.

### Backup and Restore

#### Backup Volumes

```bash
# Create a backup directory
mkdir -p backups

# Backup Redis data
docker run --rm -v agenthub_redis_data:/source -v $(pwd)/backups:/backup alpine tar -czf /backup/redis-backup.tar.gz -C /source .

# Backup RabbitMQ data
docker run --rm -v agenthub_rabbitmq_data:/source -v $(pwd)/backups:/backup alpine tar -czf /backup/rabbitmq-backup.tar.gz -C /source .

# Backup Milvus data
docker run --rm -v agenthub_milvus_data:/source -v $(pwd)/backups:/backup alpine tar -czf /backup/milvus-backup.tar.gz -C /source .
```

#### Restore Volumes

```bash
# Restore Redis data
docker run --rm -v agenthub_redis_data:/destination -v $(pwd)/backups:/backup alpine sh -c "rm -rf /destination/* && tar -xzf /backup/redis-backup.tar.gz -C /destination"

# Restore RabbitMQ data
docker run --rm -v agenthub_rabbitmq_data:/destination -v $(pwd)/backups:/backup alpine sh -c "rm -rf /destination/* && tar -xzf /backup/rabbitmq-backup.tar.gz -C /destination"

# Restore Milvus data
docker run --rm -v agenthub_milvus_data:/destination -v $(pwd)/backups:/backup alpine sh -c "rm -rf /destination/* && tar -xzf /backup/milvus-backup.tar.gz -C /destination"
```

## Troubleshooting

### Common Issues

1. **Services Won't Start**
   - Check Docker logs: `docker-compose -f deploy/docker/docker-compose.dev.yml logs`
   - Verify environment variables in `.env` file
   - Ensure ports are not already in use (see [Docker Quick Guide](../docs/docker-quickguide.md))

2. **API Connection Issues**
   - Check if services are running: `docker ps`
   - Verify network connectivity between containers
   - Check for proper URL configuration in frontend environment

3. **Performance Issues**
   - Monitor resource usage: `docker stats`
   - Consider increasing container resource limits
   - Check logs for slow queries or operations

### Logs

```bash
# View logs for all services
docker-compose -f deploy/docker/docker-compose.dev.yml logs

# View logs for a specific service
docker-compose -f deploy/docker/docker-compose.dev.yml logs orchestrator

# Follow logs in real-time
docker-compose -f deploy/docker/docker-compose.dev.yml logs -f
```

### Health Checks

```bash
# Check Orchestrator health
curl http://localhost:8000/health

# Check Document Service health
curl http://localhost:8001/health

# Check Web Search Service health
curl http://localhost:8002/health
```

---

*This deployment guide was last updated on June 2, 2025.*
