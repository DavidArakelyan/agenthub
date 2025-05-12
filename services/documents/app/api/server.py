"""
FastMCP server implementation for the document service.
"""

from typing import List, Dict, Any, Optional  # noqa: F401
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastmcp import FastMCP
from pydantic import BaseModel

from app.core.document_service import DocumentService

# Initialize FastAPI app
app = FastAPI(title="Document Service MCP")

# Initialize document service
document_service = DocumentService()

# Initialize FastMCP
mcp = FastMCP(app)


# Pydantic models for request/response
class SearchRequest(BaseModel):
    query: str
    k: int = 4
    filter_criteria: Optional[Dict[str, Any]] = None


class DocumentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any]


@mcp.tool("process_document")
async def process_document(request):
    """Handle document processing requests."""
    try:
        file_path = request.data.get("file_path")
        metadata = request.data.get("metadata")

        if not file_path:
            return {"success": False, "error": "file_path is required"}

        result = await document_service.process_document(file_path, metadata)
        return {"success": True, "data": {"message": result}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool("semantic_search")
async def semantic_search(request):
    """Handle semantic search requests."""
    try:
        search_request = SearchRequest(**request.data)
        results = await document_service.semantic_search(
            query=search_request.query,
            k=search_request.k,
            filter_criteria=search_request.filter_criteria,
        )

        # Convert results to response format
        documents = [
            DocumentResponse(content=doc.page_content, metadata=doc.metadata).dict()
            for doc in results
        ]

        return {"success": True, "data": {"documents": documents}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool("get_document")
async def get_document(request):
    """Handle document retrieval requests."""
    try:
        doc_id = request.data.get("doc_id")
        if not doc_id:
            return {"success": False, "error": "doc_id is required"}

        document = await document_service.get_document_by_id(doc_id)
        if not document:
            return {"success": False, "error": "Document not found"}

        return {
            "success": True,
            "data": DocumentResponse(
                content=document.page_content, metadata=document.metadata
            ).dict(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool("delete_document")
async def delete_document(request):
    """Handle document deletion requests."""
    try:
        doc_id = request.data.get("doc_id")
        if not doc_id:
            return {"success": False, "error": "doc_id is required"}

        success = await document_service.delete_document(doc_id)
        return {
            "success": success,
            "data": {
                "message": "Document deleted successfully"
                if success
                else "Document not found"
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# File upload endpoint
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...), metadata: Optional[Dict[str, Any]] = None
):
    """Handle file uploads."""
    try:
        # Save the uploaded file
        file_path = f"./uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Process the document
        result = await document_service.process_document(file_path, metadata)
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_file_upload(file_path: str, metadata: dict) -> str:
    """Handle file upload and process the document to update the knowledge base."""
    try:
        result = await document_service.process_document(file_path, metadata)
        return result
    except Exception as e:
        return f"Error processing document: {str(e)}"
