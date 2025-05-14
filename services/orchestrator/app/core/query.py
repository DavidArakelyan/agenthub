"""
Query models and types for the agent workflow.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class GeneratorType(str, Enum):
    """Types of generators available in the system."""

    CODE = "code"
    DOCUMENT = "document"
    NONE = "none"


class CodeLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "py"
    TYPESCRIPT = "ts"
    CPP = "cpp"
    JAVA = "java"


class DocumentFormat(str, Enum):
    """Supported document formats."""

    TEXT = "txt"
    MARKDOWN = "md"
    DOC = "doc"
    PDF = "pdf"


class BaseQuery(BaseModel):
    """Base class for all query types."""

    content: str
    needs_web_search: bool = False
    needs_document_processing: bool = False


class SimpleQuery(BaseQuery):
    """Query that can be answered directly without generation."""

    pass


class ComplexQuery(BaseQuery):
    """Query that requires code or document generation."""

    generator_type: GeneratorType = GeneratorType.NONE
    code_language: Optional[CodeLanguage] = None
    document_format: Optional[DocumentFormat] = None
