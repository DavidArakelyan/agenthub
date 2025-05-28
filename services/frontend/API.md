# API Documentation

This document describes the API endpoints used between the frontend and orchestrator services.

## Base URL
```
http://localhost:8000
```

## Endpoints

### Chat Operations

#### Create New Chat
- **POST** `/chat/new`
- **Response:**
  ```typescript
  {
    success: boolean;
    data: {
      chatId: string;
    };
  }
  ```

#### Get Chat History
- **GET** `/chat/{chatId}/history`
- **Response:**
  ```typescript
  {
    success: boolean;
    data: Array<{
      id: string;
      text: string;
      type: 'user' | 'reply';
      files?: File[];
      timestamp: string;
    }>;
  }
  ```

#### Send Message
- **POST** `/chat/message`
- **Request Body:** FormData with:
  - chat_id: string
  - message: string
  - files: File[] (optional)
- **Response:**
  ```typescript
  {
    success: boolean;
    data: {
      message: string;
      canvas_content?: {
        type: 'code' | 'document';
        format: string;
        content: string;
      };
      task_status?: {
        needs_web_search: boolean;
        needs_document_processing: boolean;
      };
    };
  }
  ```

#### Delete Chat
- **DELETE** `/chat/{chatId}`
- **Response:**
  ```typescript
  {
    success: boolean;
  }
  ```

### Document Operations

#### Upload Document
- **POST** `/documents/upload`
- **Request Body:** FormData with:
  - file: File
  - metadata?: Record<string, any>
- **Response:**
  ```typescript
  {
    success: boolean;
    data: {
      id: string;
      content: string;
      metadata: Record<string, any>;
    };
  }
  ```

#### Search Documents
- **GET** `/documents/search`
- **Query Parameters:**
  - query: string
  - k: number (default: 4)
- **Response:**
  ```typescript
  {
    success: boolean;
    data: Array<{
      id: string;
      content: string;
      metadata: Record<string, any>;
    }>;
  }
  ```

### Web Search Operations

#### Perform Web Search
- **GET** `/websearch/search`
- **Query Parameters:**
  - query: string
- **Response:**
  ```typescript
  {
    success: boolean;
    data: any;
  }
  ```

### Save Content Operations

#### Save Generated Content
- **POST** `/save`
- **Request Body:**
  ```typescript
  {
    content: string;
    format: string;
    filename: string;
  }
  ```
- **Response:**
  ```typescript
  {
    success: boolean;
    data: {
      path: string;
      message: string;
    };
  }
  ```

## Error Handling

All endpoints follow this error response format:
```typescript
{
  success: false;
  error: {
    code: string;
    message: string;
    data?: any;
  };
}
```

Common error codes:
- `NETWORK_ERROR`: Connection issues
- `UNAUTHORIZED`: Authentication required
- `INVALID_REQUEST`: Bad request format
- `INTERNAL_ERROR`: Server-side error
- `NOT_FOUND`: Resource not found

## File Size Limits
- Maximum file size: 10MB (10485760 bytes)
- Configured via `REACT_APP_MAX_FILE_SIZE` environment variable

## Authentication
All requests should include an Authorization header when authentication is implemented:
```
Authorization: Bearer ${token}
```
