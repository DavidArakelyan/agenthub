# Agent Orchestrator Service

The Agent Orchestrator Service is a FastAPI-based service that implements an intelligent agent workflow using LangGraph and the Model Context Protocol. It provides a flexible and dynamic workflow for processing user requests through various specialized agents.

## Architecture

The service implements a state-based workflow using LangGraph, with the following key components:

### State Management

The workflow maintains state through the `AgentState` class, which includes:
- `messages`: List of conversation messages
- `current_step`: Current execution step
- `task_status`: Task execution status and flags
- `context`: Additional context for the current task

### Workflow Components

1. **Task Planner**
   - Analyzes user requests
   - Determines if web search or document processing is needed
   - Returns a structured plan with boolean flags for required services

2. **Web Searcher** (Conditional)
   - Activated only when web search is required
   - Performs web searches based on task requirements
   - Adds search results to the context

3. **Document Processor** (Conditional)
   - Activated only when document processing is needed
   - Processes and embeds documents
   - Adds document context to the state

4. **Response Generator**
   - Generates final responses based on collected information
   - Uses context from all previous steps
   - Updates the conversation with the response

### Workflow Logic

The workflow follows a dynamic routing pattern:

1. **Entry Point**: Task Planner
   - Analyzes the user's request
   - Determines required services through JSON response:
     ```json
     {
       "needs_web_search": boolean,
       "needs_document_processing": boolean
     }
     ```

2. **Conditional Routing**:
   - If web search needed → Web Searcher → Response Generator
   - If document processing needed → Document Processor → Response Generator
   - If neither needed → directly to Response Generator

3. **Final Step**:
   - Response Generator creates the final response
   - Updates conversation state
   - Marks workflow as complete

## API Endpoints

- `POST /chat/new`: Create a new chat session
- `GET /chat/{chat_id}/history`: Get chat history
- `POST /chat/message`: Send a message to the chat
- `DELETE /chat/{chat_id}`: Delete a chat
- `GET /health`: Health check endpoint

## Configuration

The service uses environment variables for configuration:
- `OPENAI_API_KEY`: OpenAI API key
- `MODEL_NAME`: LLM model name (default: "gpt-3.5-turbo")
- `TEMPERATURE`: LLM temperature (default: 0.7)

## Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the service:
   ```bash
   ./run.sh
   ```

The service will be available at `http://localhost:8000`. 