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
import sys
from pathlib import Path
import os


# Create function to set up logging
def setup_logging():
    """Set up logging configuration."""
    # Set up logging directory - use absolute path from workspace root
    log_dir = Path(__file__).resolve().parents[2] / "logs"  # Changed to correct path
    try:
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "orchestrator.log"

        # Ensure we have write permissions and create the file if it doesn't exist
        if not log_file.exists():
            log_file.touch(mode=0o644)
        if not os.access(log_file, os.W_OK):
            print(f"Warning: No write access to {log_file}")
            return False

        # Configure formatters
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Configure file handler
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

        # Configure stderr handler
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.setLevel(logging.INFO)

        # Configure root logger with both handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        # root_logger.addHandler(stderr_handler)

        return True
    except Exception as e:
        print(f"Error setting up logging: {e}")
        return False


# Set up logging
setup_logging()

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set levels for specific modules
# logging.getLogger("app.core.workflow").setLevel(logging.INFO)
# logging.getLogger("app.core.nodes").setLevel(logging.INFO)


def load_environment() -> None:
    """Load environment variables, prioritizing existing environment variables."""
    # First check if OPENAI_API_KEY is already set in the environment
    if os.environ.get("OPENAI_API_KEY"):
        logger.info("OPENAI_API_KEY already set in environment")
        return
    
    # If not set, try to load from .env file
    try:
        workspace_env = Path(__file__).resolve().parents[4] / ".env"
        logger.debug(f"Looking for .env at: {workspace_env}")
        if workspace_env.exists():
            logger.info(f"Loading environment from {workspace_env}")
            load_dotenv(dotenv_path=workspace_env, verbose=True, override=True)
        else:
            # Try alternative locations as fallback
            app_env = Path(__file__).resolve().parents[2] / ".env"
            if app_env.exists():
                logger.info(f"Loading environment from {app_env}")
                load_dotenv(dotenv_path=app_env, verbose=True, override=True)
            else:
                logger.warning("No .env file found")
    except IndexError:
        logger.warning("Error navigating directory structure, trying alternative paths")
        # Try current directory as last resort
        current_env = Path(".env")
        if current_env.exists():
            logger.info(f"Loading environment from current directory: {current_env}")
            load_dotenv(dotenv_path=current_env, verbose=True, override=True)
        else:
            logger.warning("No .env file found in any location")


# Load environment variables from root .env file
load_environment()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Agent Orchestrator"

    # OpenAI Configuration - will be loaded from environments
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
    main_model_name: str = "o4-mini"
    #main_model_name: str = "gpt-4.1"
    #main_model_temperature: float = 0.7

    # Code generation model
    #code_model_name: str = "o3"
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
