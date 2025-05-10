"""
Test configuration and fixtures.
"""
import pytest
import os
import tempfile
from pathlib import Path

@pytest.fixture(autouse=True)
def test_env():
    """Set up test environment variables."""
    # Create temporary directories
    temp_dir = tempfile.mkdtemp()
    os.environ["PERSIST_DIRECTORY"] = os.path.join(temp_dir, "chroma")
    os.environ["UPLOAD_DIR"] = os.path.join(temp_dir, "uploads")
    
    # Create directories
    Path(os.environ["PERSIST_DIRECTORY"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir) 