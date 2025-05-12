# Docker and Port Management Quick Guide

## Container Management Commands

### Basic Container Operations
```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Start a container
docker start <container_name>

# Stop a container
docker stop <container_name>

# Stop all running containers
docker stop $(docker ps -q)

# Remove a container
docker rm <container_name>

# Remove all stopped containers
docker container prune

# Remove all unused containers, networks, images
docker system prune
```

### Container Information
```bash
# View container logs
docker logs <container_name>

# Follow container logs
docker logs -f <container_name>

# View container details
docker inspect <container_name>

# View container resource usage
docker stats
```

### Image Management
```bash
# List images
docker images

# Pull an image
docker pull <image_name>:<tag>

# Remove an image
docker rmi <image_name>

# Build an image from Dockerfile
docker build -t <image_name> .

# Remove unused images
docker image prune
```

### Docker Compose Commands
```bash
# Start services
docker-compose up

# Start services in detached mode
docker-compose up -d

# Stop services
docker-compose down

# View service logs
docker-compose logs

# Follow service logs
docker-compose logs -f

# Rebuild services
docker-compose build
```

## Port Management Commands

### Check Port Usage (macOS/Linux)

#### Using lsof
```bash
# Check specific port
lsof -i :<port_number>

# Example: Check port 8000
lsof -i :8000

# Check all ports
lsof -i -P -n
```

#### Using netstat (macOS)
```bash
# List all ports and applications
netstat -anv | grep LISTEN

# Check specific port
netstat -anv | grep <port_number>

# Example: Check port 8000
netstat -anv | grep 8000
```

#### Using netstat (Linux)
```bash
# List all listening ports
netstat -tulpn

# Check specific port
netstat -tulpn | grep <port_number>
```

### Docker Port Mapping
```bash
# View container port mappings
docker port <container_name>

# Run container with port mapping
docker run -p <host_port>:<container_port> <image_name>

# Example: Map port 8000
docker run -p 8000:8000 myapp
```

## Best Practices

1. Always use meaningful container names
2. Use version tags for images instead of 'latest'
3. Clean up unused containers and images regularly
4. Check port conflicts before starting services
5. Use docker-compose for multi-container applications
6. Monitor container logs and resource usage
7. Implement proper container health checks

## Common Port Numbers

- 80: HTTP
- 443: HTTPS
- 3000: Common development port (React, Node.js)
- 8000-8080: Common development ports (Python, Java)
- 5432: PostgreSQL
- 6379: Redis
- 27017: MongoDB
- 3306: MySQL