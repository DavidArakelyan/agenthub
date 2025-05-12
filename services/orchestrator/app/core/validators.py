from pydantic import BaseModel, Field, validator
from typing import List, Optional
from fastapi import UploadFile
import re


class MessageRequest(BaseModel):
    """Validation model for chat message requests."""

    chat_id: str = Field(..., min_length=1, description="Chat session ID")
    message: str = Field(
        ..., min_length=1, max_length=4000, description="Message content"
    )
    files: Optional[List[str]] = Field(default=None, description="List of file names")

    @validator("chat_id")
    def validate_chat_id(cls, v):
        if not re.match(r"^[a-f0-9-]+$", v):
            raise ValueError("Invalid chat ID format")
        return v

    @validator("message")
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file."""
    if not file.filename:
        raise ValueError("File must have a filename")

    # Check file extension
    allowed_extensions = {".txt", ".pdf", ".doc", ".docx", ".md"}
    file_ext = file.filename.lower().split(".")[-1]
    if f".{file_ext}" not in allowed_extensions:
        raise ValueError(
            f"File type .{file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Check file size (10MB limit)
    mb_size = 10
    MAX_FILE_SIZE = mb_size * 1024 * 1024  # 10MB in bytes
    if file.size and file.size > MAX_FILE_SIZE:
        raise ValueError(f"File size exceeds maximum limit of {mb_size}MB")
