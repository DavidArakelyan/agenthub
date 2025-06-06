"""Utility functions and validators for the workflow implementation."""

import re
from typing import List, Optional
from fastapi import UploadFile
from pydantic import BaseModel, Field, field_validator, ConfigDict


class MessageRequest(BaseModel):
    """Validation model for chat message requests."""

    model_config = ConfigDict(populate_by_name=True)

    chat_id: str = Field(..., min_length=1, description="Chat session ID")
    message: str = Field(
        ..., min_length=1, max_length=4000, description="Message content"
    )
    files: Optional[List[str]] = Field(default=None, description="List of file names")

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v):
        if not re.match(r"^[a-f0-9-]+$", v):
            raise ValueError("Invalid chat ID format")
        return v

    @field_validator("message")
    @classmethod
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


def validate_typescript_code(code: str) -> bool:
    """Validate TypeScript code for best practices and syntax.

    Args:
        code: The TypeScript code to validate.

    Returns:
        bool: True if the code follows best practices, False otherwise.
    """
    if not code or not isinstance(code, str):
        return False

    validation_rules = [
        (r"\bvar\b", False, "Avoid using 'var', prefer 'let' or 'const'"),
        (
            r"function\s+\w+\s*\([^:)]*\)",
            False,
            "Functions should have type annotations",
        ),
        (r"(interface|type)\s+\w+", True, "Missing interface or type definition"),
        (r":\s*[A-Z]\w+(\[\])?", True, "Missing type annotations"),
        (
            r"React\.(FC|FunctionComponent)<",
            True,
            "React components should use TypeScript generics",
        ),
    ]

    issues = []
    for pattern, should_exist, message in validation_rules:
        matches = bool(re.search(pattern, code))
        if should_exist != matches:
            issues.append(message)

    return len(issues) == 0


def validate_markdown_syntax(content: str) -> bool:
    """Validate Markdown content for proper syntax and structure.

    Args:
        content: The Markdown content to validate.

    Returns:
        bool: True if the content follows Markdown best practices, False otherwise.
    """
    if not content or not isinstance(content, str):
        return False

    # Basic checks for common Markdown elements
    basic_checks = [
        "#" in content,  # Headers
        "```" in content,  # Code blocks
        "[" in content and "]" in content,  # Links
        "- " in content or "* " in content,  # Lists
    ]
    return any(basic_checks)  # Changed to any() since not all MD needs all these
