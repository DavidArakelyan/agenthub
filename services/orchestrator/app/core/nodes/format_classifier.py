"""Format classifier node for workflow."""

import logging
import json
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, DocumentFormat, GeneratorType
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


def format_classifier(state: AgentState) -> AgentState:
    """Classify specific document format for document generation."""
    logger.info("Classifying document format...")
    if (
        not isinstance(state["query"], ComplexQuery)
        or state["query"].generator_type != GeneratorType.DOCUMENT
    ):
        return state

    llm = ChatOpenAI(
        #temperature=settings.main_model_temperature,
        model_name=settings.main_model_name,
        openai_api_key=settings.openai_api_key,
    )
    system_prompt = (
        "You are a document format classification agent. \n"
        "Analyze this query and determine the required document format for the task.\n"
        "If user has specified a particular format, use that. Otherwise, classify based on the task.\n"
        "Determine the best document format for this content:\n"
        "Text (txt):\n"
        "- Simple, unformatted content\n"
        "- Simple readme files and notes\n"
        "- Configuration files\n"
        "- Quick documentation\n\n"
        "Markdown (md):\n"
        "- Documentation with formatting\n"
        "- README files with links\n"
        "- Content needing version control\n"
        "- Blogs and articles\n\n"
        "Word Document (doc):\n"
        "- Formatted text with styles\n"
        "- Documents needing revision\n"
        "- Interactive content\n"
        "- Collaborative editing\n\n"
        "PDF (pdf):\n"
        "- Final documentation\n"
        "- Formal reports\n"
        "- Print-ready documents\n"
        "- Long-term archival\n\n"
        'Return JSON: {{"format": "txt" or "md" or "doc" or "pdf"}}'
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{query}"),
        ]
    )
    chain = prompt | llm
    response = chain.invoke({"query": state["query"].content})

    # Log the raw response
    logger.debug(f"Raw LLM Response (Format Classifier): {response}\n")
    logger.info(f"Raw LLM Response Content (Format Classifier): {response.content}\n")

    # Parse the response content
    result = json.loads(response.content)
    # Update the state with the format information
    state["query"].document_format = DocumentFormat(result["format"])
    return state
