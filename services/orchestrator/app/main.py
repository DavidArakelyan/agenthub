"""
Main FastAPI application for the agent orchestrator service.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime

from app.core.workflow import create_agent_workflow, initialize_state

app = FastAPI(
    title="Agent Orchestrator Service",
    description="Orchestrates LLM-based agents using LangGraph and Model Context Protocol",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for chats (replace with database in production)
chats: Dict[str, Dict] = {}


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
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")

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

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing message: {str(e)}"
        )


@app.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str):
    """Delete a chat."""
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    del chats[chat_id]
    return {"status": "success"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
