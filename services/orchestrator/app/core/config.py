"""
Configuration management for the orchestrator service.
"""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# Configure logging
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def load_environment() -> None:
    """Load environment variables from workspace root."""
    workspace_env = Path(__file__).resolve().parents[4] / ".env"
    logger.debug(f"Looking for .env at: {workspace_env}")
    if workspace_env.exists():
        logger.info(f"Loading environment from {workspace_env}")
        load_dotenv(dotenv_path=workspace_env, verbose=True, override=True)
    else:
        logger.warning(f"No .env file found at {workspace_env}")


# Load environment variables from root .env file
load_environment()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Agent Orchestrator"

    # OpenAI Configuration - will be loaded from environment
    openai_api_key: str = os.environ.get("OPENAI_API_KEY")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug(f"Initializing Settings with OpenAI key: {self.openai_api_key}")
        if not self.openai_api_key:
            logger.error("OpenAI API key is not set!")
            raise ValueError("OPENAI_API_KEY environment variable is not set")

    # Service Configuration
    environment: str = "development"
    debug: bool = False

    # Model Configurations
    # main_model_name: str = "o4-mini"
    main_model_name: str = "gpt-4.1"
    main_model_temperature: float = 0.7

    # Code generation model
    # main_model_name: str = "o3"
    code_model_name: str = "gpt-4.1"
    code_model_temperature: float = 0.2

    # Document generation model
    document_model_name: str = "gpt-4.1"
    document_model_temperature: float = 0.7

    # Document Service Configuration
    DOCUMENT_SERVICE_URL: str = (
        "http://localhost:8001"  # Default port for document service
    )
    DOCUMENT_SERVICE_TIMEOUT: int = 30  # Timeout in seconds for document service calls

    # CORS Configuration
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Frontend
        "http://localhost:8001",  # Document Service
        "http://localhost:8002",  # Web Search
    ]

    # No need for model_post_init, Pydantic will validate required fields


@lru_cache()
def get_settings() -> Settings:
    """
    Create cached settings instance.

    Returns:
        Settings: Application settings
    """
    return Settings()


# Create and export settings instance
settings = get_settings()
