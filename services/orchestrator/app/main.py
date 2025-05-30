"""
Main FastAPI application for the agent orchestrator service.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body, Request  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from app.core.workflow import (
    create_agent_workflow,
    initialize_state,
    run_workflow,
    run_workflow_async,
)

from app.core.config import settings
from app.core.exceptions import (
    AgentHubException,
    ValidationError,  # noqa: F401
    ChatNotFoundError,
    WorkflowError,  # noqa: F401
    FileProcessingError,
)
from app.core.utils import MessageRequest, validate_file
from app.core.mcp_client import init_mcp, mcp


# Debugging helper function
def debug_break():
    """
    Call this function anywhere you want to create a reliable breakpoint
    that will work with VS Code debugging. This function will be ignored
    in production but will stop execution in debug mode.
    """
    # This will be caught by VS Code's debugger when running with F5
    # and ignored otherwise
    frame = sys._getframe().f_back
    print(f"DEBUG BREAK at {frame.f_code.co_filename}:{frame.f_lineno}")
    # This is intentionally left here as a marker for the debugger
    a = 1  # VS Code will stop here when debugging


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


# Initialize FastMCP
init_mcp(app)

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
    target_format: Optional[str] = None


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
    try:
        chat_id = str(uuid.uuid4())
        chats[chat_id] = {
            "id": chat_id,
            "name": "New Chat",
            "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"success": True, "data": {"chatId": chat_id}}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Failed to create new chat",
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.get("/chat/{chat_id}/history")
async def get_chat_history(chat_id: str):
    """Get chat history."""
    try:
        if chat_id not in chats:
            return {
                "success": False,
                "error": {
                    "code": "CHAT_NOT_FOUND",
                    "message": "Chat not found",
                    "data": {"chat_id": chat_id},
                },
            }
        return {"success": True, "data": chats[chat_id]["messages"]}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Failed to fetch chat history",
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.post("/chat/message")
async def send_message(
    chat_id: str = Form(...),
    message: str = Form(...),
    files: List[UploadFile] = File(None),
):
    """Send a message to the chat."""
    try:

        # Validate request
        request_data = MessageRequest(chat_id=chat_id, message=message)  # noqa: F841

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

            # Initialize state with message and files
            state = initialize_state(message)
            if file_paths:
                state["context"]["document_path"] = file_paths[
                    0
                ]  # Use first file for now

            # Execute workflow
            final_state = await run_workflow_async(state)

            # Extract canvas content if any was generated
            canvas_content = final_state["context"].get("canvas_content")

            # Get target format if available
            target_format = None
            if (
                "query" in final_state
                and hasattr(final_state["query"], "code_language")
                and final_state["query"].code_language
            ):
                target_format = final_state["query"].code_language.value
            elif (
                "query" in final_state
                and hasattr(final_state["query"], "document_format")
                and final_state["query"].document_format
            ):
                target_format = final_state["query"].document_format.value

            # Get the last message (response from assistant)
            response_message = final_state["messages"][-1].content

            # Update chat history
            chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                text=message,
                type="user",
                timestamp=datetime.now(timezone.utc).isoformat(),
                files=[f.filename for f in files] if files else None,
            )
            chats[chat_id]["messages"].append(chat_message)

            # Add response to chat history
            response_chat_message = ChatMessage(
                id=str(uuid.uuid4()),
                text=response_message,
                type="reply",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            chats[chat_id]["messages"].append(response_chat_message)

            # Update chat metadata
            chats[chat_id]["updated_at"] = datetime.now(timezone.utc).isoformat()

            return {
                "success": True,
                "data": {
                    "message": response_message,
                    "canvas_content": canvas_content,
                    "task_status": final_state["task_status"],
                    "target_format": target_format,
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": {
                    "code": "WORKFLOW_ERROR",
                    "message": f"Error processing message: {str(e)}",
                    "data": {"type": str(type(e).__name__)},
                },
            }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(e),
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat."""
    try:
        if chat_id not in chats:
            return {
                "success": False,
                "error": {
                    "code": "CHAT_NOT_FOUND",
                    "message": "Chat not found",
                    "data": {"chat_id": chat_id},
                },
            }
        del chats[chat_id]
        return {"success": True, "data": {"message": "Chat deleted successfully"}}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Failed to delete chat",
                "data": {"type": str(type(e).__name__)},
            },
        }


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
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        document_response = DocumentResponse(
            id=doc_id,
            content=content.decode(),
            metadata=doc_metadata,
        )
        
        return {
            "success": True,
            "data": document_response.dict()
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DOCUMENT_UPLOAD_ERROR",
                "message": f"Error uploading document: {str(e)}",
                "data": {"type": str(type(e).__name__)},
            },
        }


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
            return {
                "success": False,
                "error": {
                    "code": "DOCUMENT_SEARCH_ERROR",
                    "message": f"Error searching documents: {response.error}",
                    "data": {}
                }
            }

        # Convert results to DocumentResponse format
        documents_list = [
            DocumentResponse(
                id=str(i),
                content=doc["content"],
                metadata=doc["metadata"],
            ).dict()
            for i, doc in enumerate(response.data["documents"])
        ]
        
        return {
            "success": True,
            "data": documents_list
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "DOCUMENT_SEARCH_ERROR",
                "message": f"Error searching documents: {str(e)}",
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.get("/websearch/search")
async def web_search(query: str = Query(...)):
    """Perform a web search."""
    try:
        # TODO: Implement actual web search
        # For now, return a mock response
        response_data = WebSearchResponse(
            results=[
                {
                    "title": "Sample Result",
                    "url": "https://example.com",
                    "snippet": "This is a sample search result.",
                }
            ],
            query=query,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        return {
            "success": True,
            "data": response_data.dict()
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "WEB_SEARCH_ERROR",
                "message": f"Error performing web search: {str(e)}",
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "success": True,
        "data": {"status": "healthy"}
    }


class SaveContentRequest(BaseModel):
    content: str
    format: str
    filename: str


@app.post("/save")
async def save_content(request: SaveContentRequest):
    """Save generated content to a file on the server."""
    try:
        # Create uploads/generated directory if it doesn't exist
        save_dir = UPLOAD_DIR / "generated"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Construct file path with timestamp to prevent overwrites
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_path = save_dir / f"{timestamp}_{request.filename}"

        # Write content to file
        with open(file_path, "w") as f:
            f.write(request.content)

        return {
            "success": True,
            "data": {
                "path": str(file_path),
                "message": f"Content saved successfully to {request.filename}",
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "SAVE_CONTENT_ERROR",
                "message": f"Error saving content: {str(e)}",
                "data": {"type": str(type(e).__name__)},
            },
        }


@app.get("/chat/list")
async def list_all_chats():
    """List all available chat sessions."""
    try:
        # Collect all chat sessions with basic info
        chat_list = [
            {
                "id": chat_id,
                "name": chat_info.get("name", "Untitled Chat"),
                "created_at": chat_info.get("created_at", ""),
                "updated_at": chat_info.get("updated_at", ""),
                "message_count": len(chat_info.get("messages", [])),
            }
            for chat_id, chat_info in chats.items()
        ]

        # Sort by updated_at in descending order (newest first)
        chat_list.sort(key=lambda x: x["updated_at"], reverse=True)

        return {"success": True, "data": chat_list}
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Failed to list chats",
                "data": {"type": str(type(e).__name__)},
            },
        }
