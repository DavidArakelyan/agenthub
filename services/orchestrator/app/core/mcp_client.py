"""
FastMCP client initialization and configuration.
"""

from fastapi import FastAPI
from fastmcp import FastMCP
from app.core.config import settings


def init_mcp(app: FastAPI) -> FastMCP:
    """Initialize FastMCP with document service configuration."""
    global mcp
    mcp = FastMCP(
        app,
        services={
            "document-service": {
                "url": settings.DOCUMENT_SERVICE_URL,
                "timeout": settings.DOCUMENT_SERVICE_TIMEOUT,
            }
        },
    )
    return mcp


# Global instance
mcp: FastMCP | None = None
