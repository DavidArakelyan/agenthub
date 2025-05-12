from fastapi import HTTPException, status
from typing import Any, Dict, Optional


class AgentHubException(HTTPException):
    """Base exception for AgentHub application."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        data: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.data = data or {}


class ValidationError(AgentHubException):
    """Raised when request validation fails."""

    def __init__(self, detail: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            data=data,
        )


class ChatNotFoundError(AgentHubException):
    """Raised when a chat is not found."""

    def __init__(self, chat_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found",
            error_code="CHAT_NOT_FOUND",
        )


class WorkflowError(AgentHubException):
    """Raised when there's an error in the workflow execution."""

    def __init__(self, detail: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code="WORKFLOW_ERROR",
            data=data,
        )


class FileProcessingError(AgentHubException):
    """Raised when there's an error processing files."""

    def __init__(self, detail: str, data: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code="FILE_PROCESSING_ERROR",
            data=data,
        )
