# Frontend API Service

This service handles all communication between the frontend and the backend orchestrator service.

## API Flows

### 1. Message Flow
```
Frontend (api.ts)                     Backend (main.py)
+----------------+                    +-------------------------+
|                |                    |                         |
| sendMessage()  | POST /chat/message |                         |
|                |------------------->|                         |
|                |                    | create_agent_workflow() |
|                |                    |                         |
|                |                    |                         |
|                |                    | initialize_state()      |
|                |                    |                         |
|                |                    |                         |
|                |                    | workflow.invoke()       |
|                |                    |                         |
|                |                    |                         |
|                |  ChatResponse      |                         | 
|                |<-------------------|                         |
+----------------+                    +-------------------------+
```

### 2. File Upload Flow
```
Frontend (api.ts)                            Backend (main.py)
+------------------+                         +----------------+
|                  |                         |                |
| uploadDocument() |  POST /documents/upload |                |
|                  |------------------------>|                |
|                  |                         |                |
|                  |                         | Process file   |
|                  |                         |                |
|                  |  DocumentResponse       |                |
|                  |<------------------------|                |
+------------------+                         +----------------+
```

## API Methods

### Chat Operations
- `createNewChat()`: Creates a new chat session
- `getChatHistory()`: Retrieves chat history
- `sendMessage()`: Sends a message with optional file attachments
- `deleteChat()`: Deletes a chat session

### Document Operations
- `uploadDocument()`: Uploads documents with metadata
- `searchDocuments()`: Searches through documents

### Web Search Operations
- `performWebSearch()`: Performs web searches

## Configuration

The API service is configured with:
- Base URL: `http://localhost:8000` (configurable via `REACT_APP_API_BASE_URL`)
- Maximum file size: 10MB (configurable via `REACT_APP_MAX_FILE_SIZE`)

## Error Handling

The service includes comprehensive error handling:
- Request/response logging
- Authentication token management
- File size validation
- HTTP error status handling
- Network error handling 