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
- `query_type`: Type of query ("simple" or "complex")
- `generation_type`: Type of generation needed ("code", "document", or "none")
- `target_format`: Target format for generation (e.g., "py", "cpp", "java", "txt", "doc", "pdf")

### Query Classification

The service first classifies queries into two categories:

1. **Simple Queries**
   - Within LLM's knowledge cutoff date
   - No code or document generation required
   - No additional context provided
   - Can be answered directly by the LLM

2. **Complex Queries**
   - Require recent information (post LLM cutoff)
   - Need code or document generation
   - Include additional context (attachments)
   - Require specialized processing

### Workflow Components

1. **Query Classifier**
   - Analyzes user requests
   - Determines query type (simple/complex)
   - Identifies required processing steps
   - Returns structured classification with processing flags

2. **Web Searcher** (Conditional)
   - Activated for queries needing recent information
   - Performs web searches based on task requirements
   - Adds search results to the context

3. **Document Processor** (Conditional)
   - Activated when additional context is provided
   - Processes and embeds documents
   - Adds document context to the state

4. **Code Generator** (Conditional)
   - Activated for code generation requests
   - Uses specialized GPT-4 model
   - Supports multiple languages:
     - Python (.py)
     - C++ (.cpp)
     - Java (.java)

5. **Document Generator** (Conditional)
   - Activated for document generation requests
   - Uses specialized GPT-4 model
   - Supports multiple formats:
     - Text (.txt)
     - Word (.doc)
     - PDF (.pdf)

6. **Response Generator**
   - Generates final responses based on collected information
   - Uses context from all previous steps
   - Updates the conversation with the response

### Workflow Logic

The workflow follows a dynamic routing pattern:

1. **Entry Point**: Query Classifier
   - Analyzes the user's request
   - Determines required processing through JSON response:
     ```json
     {
       "query_type": "simple" | "complex",
       "needs_web_search": boolean,
       "needs_document_processing": boolean,
       "generation_type": "code" | "document" | "none",
       "target_format": "cpp" | "py" | "java" | "txt" | "doc" | "pdf" | "none"
     }
     ```

2. **Conditional Routing**:
   - Simple queries → directly to Response Generator
   - Complex queries → appropriate processor(s):
     - Recent info needed → Web Searcher
     - Context provided → Document Processor
     - Code needed → Code Generator
     - Document needed → Document Generator
   - All processors → Response Generator

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

### OpenAI API Configuration
- `OPENAI_API_KEY`: OpenAI API key

### Model Configurations
1. **Main Decision Making Model** (o4-mini)
   - Used for query classification, web search, and response generation
   - Model: `o4-mini`
   - Temperature: 0.7

2. **Code Generation Model** (o3)
   - Specialized for code generation tasks
   - Model: `o3`
   - Temperature: 0.2 (lower for more deterministic code)

3. **Document Generation Model** (GPT-4.1)
   - Specialized for document generation tasks
   - Model: `gpt-4.1`
   - Temperature: 0.7

### Service Configuration
- `ENVIRONMENT`: Service environment (default: "development")
- `DEBUG`: Debug mode flag (default: false)

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