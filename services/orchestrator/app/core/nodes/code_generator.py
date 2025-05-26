"""Code generator node for workflow."""

import logging
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, CodeLanguage
from app.core.config import get_settings
from app.core.types import AgentState
from app.core.utils import validate_typescript_code

logger = logging.getLogger(__name__)
settings = get_settings()


def sync_code_generator(state: AgentState) -> AgentState:
    """
    Synchronous wrapper for code generation.
    """
    import asyncio

    try:
        # Try to get the existing loop
        loop = asyncio.get_event_loop()
        should_close_loop = False
    except RuntimeError:
        # Create a new loop if none exists
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        should_close_loop = True

    try:
        # Run the async code generator
        return loop.run_until_complete(code_generator(state))
    finally:
        # Only close the loop if we created it
        if should_close_loop:
            loop.close()


async def code_generator(state: AgentState) -> AgentState:
    """Generates code in the specified programming language."""
    try:
        if (
            not isinstance(state["query"], ComplexQuery)
            or state["query"].code_language is None
        ):
            raise ValueError("Invalid state for code generation")

        llm = ChatOpenAI(
            temperature=settings.code_model_temperature,
            model_name=settings.code_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # Language-specific prompts for better code generation
        language_prompts = {
            CodeLanguage.PYTHON: (
                "Generate Python code following these guidelines:\n"
                "1. Use type hints for parameters and return values\n"
                "2. Follow PEP 8 style guidelines\n"
                "3. Include docstrings for functions and classes\n"
                "4. Handle errors with try/except\n"
                "5. Use list/dict comprehensions where appropriate\n"
            ),
            CodeLanguage.TYPESCRIPT: (
                "Generate TypeScript code following these guidelines:\n"
                "1. Use strict type checking\n"
                "2. Follow Airbnb TypeScript style guide\n"
                "3. Include JSDoc comments\n"
                "4. Use async/await for asynchronous code\n"
                "5. Include error handling\n"
            ),
            CodeLanguage.JAVASCRIPT: (
                "Generate JavaScript code following these guidelines:\n"
                "1. Use modern ES6+ syntax\n"
                "2. Follow Airbnb JavaScript style guide\n"
                "3. Include JSDoc comments\n"
                "4. Use async/await for asynchronous code\n"
                "5. Include error handling\n"
            ),
            CodeLanguage.JAVA: (
                "Generate Java code following these guidelines:\n"
                "1. Follow Oracle Java code conventions\n"
                "2. Include JavaDoc comments\n"
                "3. Use appropriate access modifiers\n"
                "4. Implement proper exception handling\n"
                "5. Follow SOLID principles\n"
            ),
            CodeLanguage.CPP: (
                "Generate C++ code following these guidelines:\n"
                "1. Use modern C++17/20 features\n"
                "2. Follow Google C++ style guide\n"
                "3. Include doxygen comments\n"
                "4. Use RAII principles\n"
                "5. Use smart pointers over raw pointers\n"
            ),
            CodeLanguage.JAVA: (
                "Generate Java code following these guidelines:\n"
                "1. Use latest Java features\n"
                "2. Follow Google Java style guide\n"
                "3. Include Javadoc comments\n"
                "4. Use try-with-resources for AutoCloseable\n"
                "5. Follow SOLID principles\n"
            ),
        }

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    language_prompts.get(
                        state["query"].code_language,
                        "Generate well-structured code.",
                    ),
                ),
                ("human", "Task: {input}"),
            ]
        )
        chain = prompt | llm
        code_response = chain.invoke({"input": state["query"].content})
        # Log the raw response
        logger.debug(f"Raw LLM Response: {code_response}")
        logger.info(f"Raw LLM Response Content: {code_response.content}")

        # Add validation for TypeScript
        if state["query"].code_language == CodeLanguage.TYPESCRIPT:
            if not validate_typescript_code(code_response.content):
                logger.warning("Generated TypeScript doesn't follow best practices")
                # Regenerate with stricter guidelines
                typescript_strict_prompt = (
                    "Improve this TypeScript code following best practices:\n"
                    "1. Use strict type checking\n"
                    "2. Follow Airbnb TypeScript style guide\n"
                    "3. Include JSDoc comments\n"
                    "4. Use async/await for asynchronous code\n"
                    "5. Include error handling with try/catch\n"
                )
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", typescript_strict_prompt),
                        (
                            "human",
                            "Improve this TypeScript code following best practices:\n{code}",
                        ),
                    ]
                )
                chain = prompt | llm
                code_response = chain.invoke({"code": code_response.content})

        # Update state with generated code
        state["context"]["generated_code"] = code_response.content
        state["context"]["code_generation_completed"] = True
        logger.info(f"Code generation completed for {state['query'].code_language}")
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}")
        state["context"]["code_generation_completed"] = False
        state["context"]["error"] = str(e)
    return state
