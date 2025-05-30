"""Code generator node for workflow."""

import logging
import time as import_time
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, CodeLanguage, QueryAction
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

    # Use asyncio.run() which properly manages the event loop
    # This replaces the deprecated get_event_loop pattern
    return asyncio.run(code_generator(state))


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

        # Check if this is an update query with previous content
        is_update = (
            hasattr(state["query"], "action") 
            and state["query"].action == QueryAction.UPDATE
            and hasattr(state["query"], "previous_content")
            and state["query"].previous_content
        )

        if is_update:
            # Modify prompt for update queries
            system_prompt = language_prompts.get(
                state["query"].code_language,
                "Update the code based on the request.",
            )
            system_prompt += (
                "\n\nThis is an update request. You will be provided with the existing code and a request to modify it.\n"
                "When updating the code:\n"
                "1. Keep the overall structure and functionality intact\n"
                "2. Make only the changes requested in the update request\n"
                "3. Return the entire updated code, not just the changed parts\n"
                "4. Maintain consistent style with the original code\n"
                "5. Ensure the updated code is complete and functional\n"
            )
            
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "Original code:\n```\n{previous_code}\n```\n\nUpdate request: {input}"),
                ]
            )
            chain = prompt | llm
            code_response = chain.invoke({
                "previous_code": state["query"].previous_content,
                "input": state["query"].content
            })
        else:
            # Standard prompt for new code generation
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
        raw_response = code_response.content

        # Try to extract pure code if it's in a code block format
        pure_code = raw_response
        code_explanation = ""

        # If the response contains markdown code blocks, extract just the code
        if "```" in raw_response:
            code_blocks = raw_response.split("```")

            # Check if we have at least one complete code block
            if len(code_blocks) >= 3:
                # The text before the first code block is the explanation
                code_explanation = code_blocks[0].strip()

                # Get the code block - skip language identifier if present
                code_block = code_blocks[1]
                lines = code_block.split("\n", 1)
                if len(lines) > 1:
                    # Skip the language identifier line
                    pure_code = lines[1].strip()
                else:
                    pure_code = lines[0].strip()

                # If there's more explanation after the code block, add it
                if len(code_blocks) > 3:
                    additional_explanation = "\n\n".join(code_blocks[2:-1]).strip()
                    if additional_explanation:
                        code_explanation += "\n\n" + additional_explanation

        # Store both the raw response and the extracted pure code
        state["context"]["generated_code_raw"] = raw_response
        state["context"]["generated_code"] = pure_code
        state["context"]["code_explanation"] = code_explanation
        state["context"]["code_generation_completed"] = True
        
        # Store metadata for retrieval later
        state["context"]["generation_metadata"] = {
            "generator_type": "code",
            "code_language": state["query"].code_language.value if state["query"].code_language else None,
            "is_update": is_update,
            "file_identifier": state["query"].file_identifier if hasattr(state["query"], "file_identifier") else None
        }            # If we have a file identifier, save the content for later retrieval
        if hasattr(state["query"], "file_identifier") and state["query"].file_identifier:
            from ..nodes.content_retriever import save_generated_content
            try:
                metadata = {
                    "generator_type": "code",
                    "code_language": state["query"].code_language.value if state["query"].code_language else None,
                    "timestamp": import_time.time(),
                    "query": state["query"].content
                }
                
                # Check if this is an update query
                is_update = (
                    hasattr(state["query"], "action") 
                    and state["query"].action == QueryAction.UPDATE
                )
                
                # Include previous content metadata if available for updates
                if is_update and "context" in state and "previous_content_metadata" in state["context"]:
                    prev_metadata = state["context"]["previous_content_metadata"]
                    # Preserve important metadata fields that shouldn't change between versions
                    for key, value in prev_metadata.items():
                        if key not in ["timestamp", "query"] and key not in metadata:
                            metadata[key] = value
                
                save_generated_content(
                    state["query"].file_identifier, 
                    pure_code,
                    metadata,
                    is_update=is_update
                )
            except Exception as e:
                logger.error(f"Error saving generated content: {str(e)}")
        
        logger.info(f"Code generation completed for {state['query'].code_language}")
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}")
        state["context"]["code_generation_completed"] = False
        state["context"]["error"] = str(e)
    return state
