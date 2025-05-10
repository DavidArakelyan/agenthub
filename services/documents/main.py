"""
Main entry point for the document service.
"""
import uvicorn
from app.core.config import settings
from app.api.server import app

if __name__ == "__main__":
    uvicorn.run(
        "app.api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    ) 