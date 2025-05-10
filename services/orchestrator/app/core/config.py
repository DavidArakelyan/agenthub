"""
Configuration management for the orchestrator service.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Service Configuration
    environment: str = "development"
    debug: bool = False
    
    # Model Configuration
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    
    class Config:
        """Pydantic config class."""
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """
    Create cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings() 