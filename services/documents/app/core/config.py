"""
Configuration management for the document service.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv
import os

# Load top-level .env file
env_path = os.path.join(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    ),
    ".env",
)
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document Service"
    PORT: int = 8001  # Document service port

    # Service Configuration
    environment: str = "development"
    debug: bool = False

    # CORS Configuration
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Frontend
        "http://localhost:8000",  # Orchestrator
        "http://localhost:8002",  # Web Search
    ]

    # Server Configuration
    HOST: str = "0.0.0.0"

    # Document Processing Configuration
    UPLOAD_DIR: str = "./uploads"
    PERSIST_DIRECTORY: str = "./data/chroma"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()
