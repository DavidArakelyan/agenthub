# AgentHub

A modern chat interface application built with React and TypeScript, featuring a ChatGPT-like experience with file attachments and chat history management. The system uses a microservices architecture with LLM-based agents for intelligent task processing.

## Features

- Modern chat interface with ChatGPT-like design
- File attachment support with drag-and-drop
- Chat history management
- Multiple chat sessions
- Real-time message updates
- Responsive design
- Canvas panel for additional content
- Intelligent task processing using LLM-based agents
- Document processing and semantic search
- Web search capabilities
- Vector-based document storage and retrieval

## System Architecture

The system consists of multiple microservices:

### Frontend Service
- React + TypeScript application
- Modern UI with real-time updates
- File upload and management
- Chat history and session management

### Orchestrator Service
- FastAPI-based service
- LLM-based agent orchestration using LangGraph
- Task planning and execution
- Integration with other services
- Response generation

### Document Service
- Document processing and embedding
- Vector store integration (ChromaDB)
- Semantic search capabilities
- Support for multiple file types (txt, pdf, docx, md)
- RAG (Retrieval Augmented Generation) capabilities

### Web Search Service
- Web search functionality
- Integration with the orchestrator

### Supporting Infrastructure
- Redis for caching
- RabbitMQ for message queuing
- Milvus for vector storage
- Prometheus for monitoring
- Grafana for visualization

## Tech Stack

### Frontend
- React
- TypeScript
- CSS3
- Axios for API communication

### Backend Services
- FastAPI
- LangGraph
- LangChain
- OpenAI API
- ChromaDB
- FastMCP (Model Context Protocol)

### Infrastructure
- Docker
- Redis
- RabbitMQ
- Milvus
- Prometheus
- Grafana

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- Python 3.9 or higher
- Docker and Docker Compose
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/agenthub.git
cd agenthub
```

2. Create a `.env` file in the root directory with the following variables:
```env
OPENAI_API_KEY=your_api_key_here
ENVIRONMENT=development
```

3. Start the development environment:
```bash
docker-compose -f deploy/docker/docker-compose.dev.yml up
```

The services will be available at:
- Frontend: http://localhost:3000
- Orchestrator: http://localhost:8000
- Document Service: http://localhost:8001
- Web Search: http://localhost:8002
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090

## Project Structure

```
services/
  ├── frontend/          # React frontend application
  ├── orchestrator/      # Agent orchestration service
  ├── documents/         # Document processing service
  └── websearch/         # Web search service
deploy/
  ├── docker/           # Docker configuration files
  ├── prometheus/       # Prometheus configuration
  └── grafana/          # Grafana configuration
```

## Usage

1. Click "New Chat" to start a new conversation
2. Type your message in the input area
3. Attach files by clicking the attachment button or dragging files
4. Press Enter or click the send button to send your message
5. View your chat history in the sidebar
6. Switch between different chats by clicking on them in the sidebar

The system will:
1. Process your message through the orchestrator
2. Perform necessary web searches and document processing
3. Generate a response using LLM-based agents
4. Display the response in the chat interface

## Development

### Running Services Individually

Each service can be run independently for development:

```bash
# Frontend
cd services/frontend
npm install
npm start

# Orchestrator
cd services/orchestrator
pip install -r requirements.txt
uvicorn app.main:app --reload

# Document Service
cd services/documents
pip install -r requirements.txt
uvicorn app.main:app --reload

# Web Search Service
cd services/websearch
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Testing

Run tests for each service:

```bash
# Frontend
cd services/frontend
npm test

# Backend Services
cd services/[service_name]
pytest
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 

# Port Assignments

The system uses the following port assignments:

## Application Services
- Frontend Service: 3000 (configured in Dockerfile and docker-compose.dev.yml)
- Orchestrator Service: 8000 (configured in Dockerfile and docker-compose.dev.yml)
- Document Service: 8001 (configured in app/core/config.py PORT setting and .env)
- Web Search Service: 8002 (configured in app/main.py and Dockerfile)

## Monitoring & Visualization
- Grafana: 3001 (configured in docker-compose.dev.yml)
- Prometheus: 9090 (configured in docker-compose.dev.yml)

## Infrastructure Services
- Redis: 6379 (standard Redis port, configured in docker-compose.dev.yml)
- RabbitMQ:
  - Main port: 5672 (standard AMQP port, configured in docker-compose.dev.yml)
  - Management interface: 15672 (standard RabbitMQ management port, docker-compose.dev.yml)
- Milvus:
  - Main port: 19530 (standard Milvus port, configured in docker-compose.dev.yml)
  - Web interface: 9091 (configured in docker-compose.dev.yml)

## Port Assignment Best Practices

The port assignments in this system follow these best practices:

- Frontend and UI tools use 3000-range ports
- Backend API services use 8000-range ports
- Infrastructure services use their standard conventional ports
- No port conflicts or overlaps between services
- Clear separation between different service categories
- Well-distributed across different port ranges

This organization ensures:
- Easy memorability of service locations
- Consistent port numbering scheme
- Standard ports for infrastructure services
- Clear separation between service types
- Room for adding new services without conflicts

## Configuration Sources
Most port configurations can be overridden through:
1. Environment variables
2. Service-specific .env files
3. docker-compose.dev.yml for containerized services
4. Application configuration files (config.py)