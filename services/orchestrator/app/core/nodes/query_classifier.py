"""Query type classifier node implementation."""

from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging

from ..config import get_settings
from ..types import SimpleQuery, ComplexQuery, GeneratorType

settings = get_settings()
logger = logging.getLogger(__name__)


def query_type_classifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """First level classification: Simple vs Complex"""
    logger.info("First level classification: Simple vs Complex...\n")

    # Use settings from config
    llm = ChatOpenAI(
        temperature=settings.main_model_temperature,
        model_name=settings.main_model_name,
        openai_api_key=settings.openai_api_key,
    )

    # Preserve existing generator type and language/format if already set
    existing_generator_type = None
    existing_code_language = None
    existing_document_format = None

    if isinstance(state["query"], ComplexQuery):
        existing_generator_type = state["query"].generator_type
        existing_code_language = state["query"].code_language
        existing_document_format = state["query"].document_format

    system_prompt = (
        "You are a query classification agent. \n"
        "Classify if this query requires generation (code/document) or can be answered directly.\n"
        "Analyze the query and determine:\n"
        "1. If it's a simple query (no code or document generation requested): set 'type' in Response JSON to 'simple'\n"
        "2. If it's a complex query (needs code/doc generation): set 'type' in Response JSON to 'complex'\n"
        "3. Determine if it needs web search (needs recent info, past cutoff date): set 'needs_web_search' boolean\n"
        "4. Determine if it needs document processing (has additional context): set 'needs_document_processing' boolean\n"
        'Return JSON: {{"type": "simple" or "complex", "needs_web_search": boolean, "needs_document_processing": boolean}}'
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{query}")]
    )
    chain = prompt | llm
    response = chain.invoke({"query": state["messages"][-1].content})

    # Log the raw response
    logger.debug(f"Raw LLM Response (Query Classifier): {response}\n")
    logger.debug(f"Raw LLM Response Content (Query Classifier): {response.content}\n")

    result = json.loads(response.content)

    if result["type"] == "simple":
        state["query"] = SimpleQuery(
            content=state["messages"][-1].content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
        )
    else:
        state["query"] = ComplexQuery(
            content=state["messages"][-1].content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
            generator_type=existing_generator_type or GeneratorType.NONE,
            code_language=existing_code_language,
            document_format=existing_document_format,
        )

    logger.info(f"Query type classification result: {result}")
    logger.info(f"Query type: {type(state['query'])}")
    return state
