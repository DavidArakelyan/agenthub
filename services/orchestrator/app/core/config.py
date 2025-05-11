"""
Configuration management for the orchestrator service.
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

    # OpenAI Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")

    # Service Configuration
    environment: str = "development"
    debug: bool = False

    # Model Configuration
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7

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
