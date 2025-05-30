"""Type definitions and query models for the orchestrator service."""

from enum import Enum
from typing import Any, Dict, List, TypedDict, Union, Optional
from langchain.schema import BaseMessage
from pydantic import BaseModel


class GeneratorType(str, Enum):
    """Types of generators available in the system."""

    CODE = "code"
    DOCUMENT = "document"
    NONE = "none"

class QueryAction(str, Enum):
    """Types of query actions."""
    
    NEW = "new"
    UPDATE = "update"


class CodeLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "py"
    TYPESCRIPT = "ts"
    JAVASCRIPT = "js"
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
    action: QueryAction = QueryAction.NEW
    previous_content: Optional[str] = None
    file_identifier: Optional[str] = None  # To identify which file to update


class AgentState(TypedDict):
    """State definition for the agent workflow."""

    messages: List[BaseMessage]
    current_step: str
    task_status: Dict[str, Any]
    context: Dict[str, Any]
    query: Union[SimpleQuery, ComplexQuery]
