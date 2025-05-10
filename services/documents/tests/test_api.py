"""
Tests for the API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil
from app.api.server import app
from app.core.document_service import DocumentService

@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\nIt has multiple lines.\nFor testing purposes.")
    yield f.name
    # Cleanup after test
    Path(f.name).unlink()

def test_upload_endpoint(client, sample_text_file):
    """Test the file upload endpoint."""
    with open(sample_text_file, 'rb') as f:
        response = client.post(
            "/upload",
            files={"file": f},
            json={"metadata": {"type": "test"}}
        )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Document processed successfully"

def test_mcp_semantic_search(client, sample_text_file):
    """Test the semantic search MCP endpoint."""
    # First upload a document
    with open(sample_text_file, 'rb') as f:
        client.post("/upload", files={"file": f})
    
    # Then search for it
    search_data = {
        "action": "semantic_search",
        "data": {
            "query": "test document",
            "k": 1
        }
    }
    
    response = client.post("/mcp", json=search_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["success"] is True
    assert len(result["data"]["documents"]) > 0
    assert "test document" in result["data"]["documents"][0]["content"].lower()

def test_mcp_get_document(client, sample_text_file):
    """Test the get document MCP endpoint."""
    # First upload a document
    with open(sample_text_file, 'rb') as f:
        client.post("/upload", files={"file": f})
    
    # Search to get document ID
    search_data = {
        "action": "semantic_search",
        "data": {
            "query": "test document",
            "k": 1
        }
    }
    search_response = client.post("/mcp", json=search_data)
    doc_id = search_response.json()["data"]["documents"][0]["metadata"]["id"]
    
    # Get document by ID
    get_doc_data = {
        "action": "get_document",
        "data": {
            "doc_id": doc_id
        }
    }
    
    response = client.post("/mcp", json=get_doc_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["success"] is True
    assert "test document" in result["data"]["content"].lower()

def test_mcp_delete_document(client, sample_text_file):
    """Test the delete document MCP endpoint."""
    # First upload a document
    with open(sample_text_file, 'rb') as f:
        client.post("/upload", files={"file": f})
    
    # Search to get document ID
    search_data = {
        "action": "semantic_search",
        "data": {
            "query": "test document",
            "k": 1
        }
    }
    search_response = client.post("/mcp", json=search_data)
    doc_id = search_response.json()["data"]["documents"][0]["metadata"]["id"]
    
    # Delete document
    delete_data = {
        "action": "delete_document",
        "data": {
            "doc_id": doc_id
        }
    }
    
    response = client.post("/mcp", json=delete_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["success"] is True
    
    # Verify document is deleted
    get_doc_data = {
        "action": "get_document",
        "data": {
            "doc_id": doc_id
        }
    }
    get_response = client.post("/mcp", json=get_doc_data)
    assert get_response.json()["success"] is False 