"""
Main FastAPI application for the agent orchestrator service.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import os
from pathlib import Path
import json
from fastmcp import FastMCP

from app.core.workflow import create_agent_workflow, initialize_state
from app.core.config import settings
from app.core.exceptions import (
    AgentHubException,
    ValidationError,
    ChatNotFoundError,
    WorkflowError,
    FileProcessingError,
)
from app.core.validators import MessageRequest, validate_file

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Orchestrates LLM-based agents using LangGraph and Model Context Protocol",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(AgentHubException)
async def agent_hub_exception_handler(request: Request, exc: AgentHubException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.error_code, "message": exc.detail, "data": exc.data},
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "data": {"type": str(type(exc).__name__)},
            },
        },
    )


# Initialize FastMCP with document service configuration
mcp = FastMCP(
    app,
    services={
        "document-service": {
            "url": settings.DOCUMENT_SERVICE_URL,
            "timeout": settings.DOCUMENT_SERVICE_TIMEOUT,
        }
    },
)

# In-memory storage for chats and documents (replace with database in production)
chats: Dict[str, Dict] = {}
documents: Dict[str, Dict] = {}

# Create upload directory if it doesn't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class ChatMessage(BaseModel):
    id: str
    text: str
    type: str
    timestamp: str
    files: Optional[List[str]] = None


class ChatResponse(BaseModel):
    message: str
    canvas_content: Optional[str] = None
    task_status: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]


class WebSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    timestamp: str


class ChatMessageRequest(BaseModel):
    chat_id: str
    message: str
    files: Optional[List[str]] = None


@app.post("/chat/new")
async def create_new_chat():
    """Create a new chat session."""
    chat_id = str(uuid.uuid4())
    chats[chat_id] = {
        "id": chat_id,
        "name": "New Chat",
        "messages": [],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    return {"chatId": chat_id}


@app.get("/chat/{chat_id}/history")
async def get_chat_history(chat_id: str):
    """Get chat history."""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chats[chat_id]["messages"]


@app.post("/chat/message")
async def send_message(
    chat_id: str = Form(...),
    message: str = Form(...),
    files: List[UploadFile] = File(None),
):
    """Send a message to the chat."""
    try:
        # Validate request
        request_data = MessageRequest(chat_id=chat_id, message=message)

        if chat_id not in chats:
            raise ChatNotFoundError(chat_id)

        # Process uploaded files if any
        file_paths = []
        if files:
            for file in files:
                try:
                    validate_file(file)
                    file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
                    with open(file_path, "wb") as buffer:
                        content = await file.read()
                        buffer.write(content)
                    file_paths.append(str(file_path))
                except ValueError as e:
                    raise FileProcessingError(str(e))

        try:
            # Initialize workflow
            workflow = create_agent_workflow()

            # Initialize state with message
            state = initialize_state(message)

            # Execute workflow
            final_state = workflow.invoke(state)

            # Create response
            response = ChatResponse(
                message=final_state["messages"][-1].content,
                task_status=final_state.get("task_status"),
                canvas_content=final_state.get("canvas_content"),
            )

            # Update chat history
            chats[chat_id]["messages"].append(
                {
                    "id": str(uuid.uuid4()),
                    "text": message,
                    "type": "user",
                    "timestamp": datetime.utcnow().isoformat(),
                    "files": file_paths,
                }
            )

            chats[chat_id]["messages"].append(
                {
                    "id": str(uuid.uuid4()),
                    "text": response.message,
                    "type": "reply",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

            chats[chat_id]["updated_at"] = datetime.utcnow().isoformat()

            return {"success": True, "data": response}

        except Exception as e:
            raise WorkflowError(f"Error processing message: {str(e)}")

    except AgentHubException:
        raise
    except Exception as e:
        raise WorkflowError(f"Unexpected error: {str(e)}")


@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat."""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    del chats[chat_id]
    return {"status": "success"}


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    """Upload a document for processing."""
    try:
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())

        # Save file to upload directory
        file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Parse metadata if provided
        doc_metadata = {}
        if metadata:
            try:
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                doc_metadata = {"original_metadata": metadata}

        # Process document using document service via FastMCP
        response = await mcp.call(
            service="document-service",
            method="process_document",
            data={"file_path": str(file_path), "metadata": doc_metadata},
        )

        if not response.success:
            raise HTTPException(
                status_code=500, detail=f"Error processing document: {response.error}"
            )

        # Store document information
        documents[doc_id] = {
            "id": doc_id,
            "filename": file.filename,
            "path": str(file_path),
            "content": content.decode(),
            "metadata": doc_metadata,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        return DocumentResponse(
            id=doc_id,
            content=content.decode(),
            metadata=doc_metadata,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error uploading document: {str(e)}"
        )


@app.get("/documents/search")
async def search_documents(
    query: str = Query(...),
    k: int = Query(4, ge=1, le=20),
):
    """Search through uploaded documents using semantic search."""
    try:
        # Perform semantic search using document service via FastMCP
        response = await mcp.call(
            service="document-service",
            method="semantic_search",
            data={"query": query, "k": k},
        )

        if not response.success:
            raise HTTPException(
                status_code=500, detail=f"Error searching documents: {response.error}"
            )

        # Convert results to DocumentResponse format
        return [
            DocumentResponse(
                id=str(i),
                content=doc["content"],
                metadata=doc["metadata"],
            )
            for i, doc in enumerate(response.data["documents"])
        ]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching documents: {str(e)}"
        )


@app.get("/websearch/search")
async def web_search(query: str = Query(...)):
    """Perform a web search."""
    try:
        # TODO: Implement actual web search
        # For now, return a mock response
        return WebSearchResponse(
            results=[
                {
                    "title": "Sample Result",
                    "url": "https://example.com",
                    "snippet": "This is a sample search result.",
                }
            ],
            query=query,
            timestamp=datetime.utcnow().isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error performing web search: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
