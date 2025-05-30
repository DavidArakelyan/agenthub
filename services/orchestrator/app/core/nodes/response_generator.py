"""Response generator node for workflow."""

import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from app.core.types import ComplexQuery, GeneratorType
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


def response_generator(state: AgentState) -> AgentState:
    """Generates the final response based on collected information."""
    logger.info("Generates the final response based on collected information.\n")
    try:
        llm = ChatOpenAI(
            #temperature=settings.main_model_temperature,
            model_name=settings.main_model_name,
            openai_api_key=settings.openai_api_key,
        )

        generation_type = (
            state["query"].generator_type
            if isinstance(state["query"], ComplexQuery)
            else GeneratorType.NONE
        )

        if generation_type == GeneratorType.CODE:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a programming assistant providing context for generated code.\n"
                        "For the code you're describing:\n"
                        "1. Explain the key components and their purpose\n"
                        "2. Highlight any important design patterns or techniques used\n"
                        "3. Note any assumptions or requirements\n"
                        "4. Suggest potential improvements or alternatives\n"
                        "5. Include any relevant usage examples\n",
                    ),
                    ("human", "Context: {context}\nDescribe the generated solution."),
                ]
            )
        elif generation_type == GeneratorType.DOCUMENT:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a documentation assistant providing context for generated content.\n"
                        "For the document you're describing:\n"
                        "1. Summarize the main sections and their purpose\n"
                        "2. Explain the document structure and organization\n"
                        "3. Highlight key information or takeaways\n"
                        "4. Note any formatting or style conventions used\n"
                        "5. Suggest how to best use or navigate the document\n",
                    ),
                    ("human", "Context: {context}\nDescribe the generated content."),
                ]
            )
        else:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful assistant providing information based on:\n"
                        "1. Direct knowledge when available\n"
                        "2. Web search results if performed\n"
                        "3. Processed documents if analyzed\n"
                        "Synthesize the information into a clear, concise response.\n",
                    ),
                    (
                        "human",
                        "Query: {query}\nContext: {context}\nProvide a comprehensive answer.",
                    ),
                ]
            )

        # Prepare generated content for canvas if any
        if isinstance(state["query"], ComplexQuery):
            if state["query"].generator_type == GeneratorType.CODE:
                # Store only the pure generated code without explanatory content
                state["context"]["canvas_content"] = state["context"].get(
                    "generated_code", ""
                )

                # Store the target format for file extension determination
                state["context"]["target_format"] = (
                    state["query"].code_language.value
                    if state["query"].code_language
                    else None
                )

                # Include any code explanation in the context for the response
                code_explanation = state["context"].get("code_explanation", "")
                if code_explanation:
                    state["context"]["explanation"] = code_explanation

            elif state["query"].generator_type == GeneratorType.DOCUMENT:
                # Store only the pure generated document without explanatory content
                state["context"]["canvas_content"] = state["context"].get(
                    "generated_document", ""
                )

                # Store the target format for file extension determination
                state["context"]["target_format"] = (
                    state["query"].document_format.value
                    if state["query"].document_format
                    else None
                )

                # Include any document explanation in the context for the response
                document_explanation = state["context"].get("document_explanation", "")
                if document_explanation:
                    state["context"]["explanation"] = document_explanation

        chain = prompt | llm
        # Always pass both query and context
        input_data = {
            "query": state["messages"][-1].content,
            "context": str(state["context"]),
        }
        response = chain.invoke(input_data)

        # Update state with just the content of the response
        state["messages"].append(SystemMessage(content=response.content))
        state["current_step"] = "end"
        return state
    except Exception as e:
        logger.error(f"Error in response generation: {str(e)}")
        state["context"]["error"] = str(e)
        return state
