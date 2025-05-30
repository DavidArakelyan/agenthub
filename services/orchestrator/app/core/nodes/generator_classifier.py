"""Generator type classifier node implementation."""

from typing import Any, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
import logging

from app.core.config import get_settings
from app.core.types import ComplexQuery, GeneratorType

settings = get_settings()
logger = logging.getLogger(__name__)


def generator_type_classifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """Second level: Classify between Code vs Document generation"""
    logger.info("Second level: Classify between Code vs Document generation...\n")

    # Add entry logging
    logger.debug("Entering generator_type_classifier")
    logger.debug(f"State entering generator_type_classifier: {state}")

    if not isinstance(state["query"], ComplexQuery):
        return state

    llm = ChatOpenAI(
        #temperature=settings.main_model_temperature,
        model_name=settings.main_model_name,
        openai_api_key=settings.openai_api_key,
    )

    system_prompt = (
        "You are a classification agent determining the type of generation required. \n"
        "Analyze this query and determine if it needs code or document generation.\n"
        "Code generation is needed for:\n"
        "- Writing functions, classes, or programs\n"
        "- Implementing algorithms or data structures\n"
        "- Creating scripts or applications\n\n"
        "Document generation is needed for:\n"
        "- Creating documentation or reports\n"
        "- Generating formatted text content\n"
        "- Producing structured documents\n\n"
        'Return JSON: {{"generator_type": "code" or "document"}}'
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
    logger.debug(f"Raw LLM Response (Generation Type Classifier): {response}\n")
    logger.info(
        f"Raw LLM Response Content (Generation Type Classifier): {response.content}\n"
    )

    # Parse the response content and update the state
    result = json.loads(response.content)
    state["query"].generator_type = GeneratorType(result["generator_type"])

    return state
