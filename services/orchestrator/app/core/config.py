"""
Configuration management for the orchestrator service.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field  # noqa: F401
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
    PROJECT_NAME: str = "Agent Orchestrator"

    # OpenAI Configuration
    OPENAI_API_KEY: str

    # Service Configuration
    environment: str = "development"
    debug: bool = False

    # Model Configurations
    # Main decision making model (o4-mini)
    main_model_name: str = "o4-mini"
    main_model_temperature: float = 0.7

    # Code generation model (o3)
    code_model_name: str = "o3"
    code_model_temperature: float = 0.2

    # Document generation model (GPT-4.1)
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

    class Config:
        """Pydantic config class."""

        env_file = env_path
        case_sensitive = True
        env_prefix = ""
        extra = "ignore"
        validate_by_name = True


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
