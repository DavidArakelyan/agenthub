"""Language classifier node for workflow."""

import logging
import json
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, CodeLanguage, GeneratorType
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


def language_classifier(state: AgentState) -> AgentState:
    """Classify specific programming language for code generation."""
    logger.info("Classifying programming language...")
    if (
        not isinstance(state["query"], ComplexQuery)
        or state["query"].generator_type != GeneratorType.CODE
    ):
        return state

    llm = ChatOpenAI(
        temperature=settings.main_model_temperature,
        model_name=settings.main_model_name,
        openai_api_key=settings.openai_api_key,
    )
    system_prompt = (
        "You are a programming language classifier. \n"
        "Analyze this query and determine the best language for the task.\n"
        "Consider the following languages:\n"
        "- Python (py): for data, AI, scripting\n"
        "- TypeScript (ts): for web, Node.js\n"
        "- JavaScript (js): for web, basic scripting\n"
        "- C++ (cpp): for systems, performance\n"
        "- Java (java): for enterprise, Android\n\n"
        'Return JSON: {{"language": "py" or "ts" or "js" or "cpp" or "java"}}'
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
    logger.debug(f"Raw LLM Response (Language Classifier): {response}\n")
    logger.info(f"Raw LLM Response Content (Language Classifier): {response.content}\n")

    # Parse the response content
    result = json.loads(response.content)
    # Update the state with the language information
    state["query"].code_language = CodeLanguage(result["language"])
    return state
