"""Language classifier node for workflow."""

import logging
import json
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, CodeLanguage, GeneratorType, QueryAction
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
        
    # If this is an update query and we already have a code_language, use that
    if (isinstance(state["query"], ComplexQuery) and 
        hasattr(state["query"], "action") and 
        state["query"].action == QueryAction.UPDATE and
        state["query"].code_language is not None):
        logger.info(f"Update query with existing language: {state['query'].code_language}")
        return state
        
    # If we have previous content metadata with code_language, use that for updates
    if (isinstance(state["query"], ComplexQuery) and
        hasattr(state["query"], "action") and 
        state["query"].action == QueryAction.UPDATE and
        "context" in state and
        "previous_content_metadata" in state["context"] and
        "code_language" in state["context"]["previous_content_metadata"]):
        lang = state["context"]["previous_content_metadata"]["code_language"]
        state["query"].code_language = CodeLanguage(lang)
        logger.info(f"Using language from previous content metadata: {lang}")
        return state
    
    # Fallback to language detection for new queries or if no language info is available
    llm = ChatOpenAI(
        #temperature=settings.main_model_temperature,
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
