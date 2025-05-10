"""
Tests for the document service core functionality.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from app.core.document_service import DocumentService

@pytest.fixture
def document_service():
    """Create a temporary document service instance for testing."""
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    service = DocumentService(
        persist_directory=temp_dir,
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        chunk_size=100,
        chunk_overlap=20
    )
    yield service
    # Cleanup after tests
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_text_file():
    """Create a sample text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\nIt has multiple lines.\nFor testing purposes.")
    yield f.name
    # Cleanup after test
    Path(f.name).unlink()

async def test_process_document(document_service, sample_text_file):
    """Test document processing."""
    # Process document
    result = await document_service.process_document(
        file_path=sample_text_file,
        metadata={"type": "test", "source": "pytest"}
    )
    
    assert result == "Document processed successfully"
    
    # Verify document was stored
    search_results = await document_service.semantic_search(
        query="test document",
        k=1
    )
    assert len(search_results) > 0
    assert "test document" in search_results[0].page_content.lower()

async def test_semantic_search(document_service, sample_text_file):
    """Test semantic search functionality."""
    # Process document first
    await document_service.process_document(sample_text_file)
    
    # Test search
    results = await document_service.semantic_search(
        query="testing purposes",
        k=1
    )
    
    assert len(results) > 0
    assert "testing purposes" in results[0].page_content.lower()

async def test_get_document_by_id(document_service, sample_text_file):
    """Test document retrieval by ID."""
    # Process document
    await document_service.process_document(sample_text_file)
    
    # Get first document ID
    search_results = await document_service.semantic_search(
        query="test document",
        k=1
    )
    doc_id = search_results[0].metadata.get("id")
    
    # Retrieve document
    document = await document_service.get_document_by_id(doc_id)
    assert document is not None
    assert "test document" in document.page_content.lower()

async def test_delete_document(document_service, sample_text_file):
    """Test document deletion."""
    # Process document
    await document_service.process_document(sample_text_file)
    
    # Get document ID
    search_results = await document_service.semantic_search(
        query="test document",
        k=1
    )
    doc_id = search_results[0].metadata.get("id")
    
    # Delete document
    success = await document_service.delete_document(doc_id)
    assert success is True
    
    # Verify document is deleted
    document = await document_service.get_document_by_id(doc_id)
    assert document is None 