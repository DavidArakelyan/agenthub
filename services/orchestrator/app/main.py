"""
Main FastAPI application for the agent orchestrator service.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from app.core.workflow import create_agent_workflow, initialize_state

app = FastAPI(
    title="Agent Orchestrator Service",
    description="Orchestrates LLM-based agents using LangGraph and Model Context Protocol",
    version="0.1.0"
)

class QueryRequest(BaseModel):
    """Request model for agent queries."""
    query: str
    context: Dict[str, Any] = {}

class QueryResponse(BaseModel):
    """Response model for agent queries."""
    response: str
    task_status: Dict[str, Any]
    steps_taken: List[str]

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a query using the agent workflow.
    
    Args:
        request: QueryRequest containing the query and optional context
        
    Returns:
        QueryResponse containing the agent's response and execution details
    """
    try:
        # Initialize workflow
        workflow = create_agent_workflow()
        
        # Initialize state with query
        state = initialize_state(request.query)
        
        # Add any provided context
        state["context"].update(request.context)
        
        # Execute workflow
        final_state = workflow.invoke(state)
        
        return QueryResponse(
            response=final_state["messages"][-1].content,
            task_status=final_state["task_status"],
            steps_taken=[msg.content for msg in final_state["messages"]]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"} 