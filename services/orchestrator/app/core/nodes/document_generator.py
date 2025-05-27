"""Document generator node for workflow."""

import logging
from langchain_openai import ChatOpenAI  # Updated import
from langchain_core.prompts import ChatPromptTemplate
from app.core.types import ComplexQuery, DocumentFormat
from app.core.config import get_settings
from app.core.types import AgentState
from app.core.utils import validate_markdown_syntax

logger = logging.getLogger(__name__)
settings = get_settings()


def sync_document_generator(state: AgentState) -> AgentState:
    """
    Synchronous wrapper for document generation.
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
        # Run the async document generator
        return loop.run_until_complete(document_generator(state))
    finally:
        # Only close the loop if we created it
        if should_close_loop:
            loop.close()


async def document_generator(state: AgentState) -> AgentState:
    """Generates documents in the specified format."""
    try:
        if (
            not isinstance(state["query"], ComplexQuery)
            or state["query"].document_format is None
        ):
            raise ValueError("Invalid state for document generation")

        llm = ChatOpenAI(
            temperature=settings.document_model_temperature,
            model_name=settings.document_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # New detailed format-specific prompts
        format_prompts = {
            DocumentFormat.TEXT: (
                "Generate plain text content following these guidelines:\n"
                "1. Use clear headings and sections\n"
                "2. Include proper paragraph breaks\n"
                "3. Use consistent indentation for lists\n"
                "4. Keep line lengths reasonable\n"
                "5. Use ASCII characters only\n"
            ),
            DocumentFormat.MARKDOWN: (
                "Generate Markdown content following these guidelines:\n"
                "1. Use proper Markdown syntax for headings\n"
                "2. Include links and images with proper syntax\n"
                "3. Use code blocks for code snippets\n"
                "4. Include lists and tables with proper formatting\n"
                "5. Use blockquotes for citations\n"
            ),
            DocumentFormat.DOC: (
                "Generate Word-compatible content following these guidelines:\n"
                "1. Use proper heading levels (H1, H2, etc.)\n"
                "2. Include a table of contents structure\n"
                "3. Use consistent font styles\n"
                "4. Include page break hints where appropriate\n"
                "5. Structure content for easy formatting\n"
            ),
            DocumentFormat.PDF: (
                "Generate PDF-suitable content following these guidelines:\n"
                "1. Include a clear document structure\n"
                "2. Use formal section numbering\n"
                "3. Include proper citations if needed\n"
                "4. Format tables and figures appropriately\n"
                "5. Include metadata hints (title, author, etc.)\n"
            ),
        }

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    format_prompts.get(
                        state["query"].document_format,
                        "Generate well-structured content.",
                    ),
                ),
                ("human", "Task: {input}"),
            ]
        )
        chain = prompt | llm
        doc_response = chain.invoke({"input": state["query"].content})
        # Log the raw response
        logger.debug(f"Raw LLM Response: {doc_response}")
        logger.info(f"Raw LLM Response Content: {doc_response.content}")

        # Add validation for Markdown
        if state["query"].document_format == DocumentFormat.MARKDOWN:
            if not validate_markdown_syntax(doc_response.content):
                logger.warning("Generated Markdown doesn't follow best practices")
                # Regenerate with stricter guidelines
                markdown_strict_prompt = (
                    "Improve this Markdown following best practices:\n"
                    "1. Use proper Markdown syntax for headings\n"
                    "2. Include links and images with proper syntax\n"
                    "3. Use code blocks for code snippets\n"
                    "4. Include lists and tables with proper formatting\n"
                    "5. Use blockquotes for citations\n"
                )
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", markdown_strict_prompt),
                        (
                            "human",
                            "Improve this Markdown following best practices:\n{doc}",
                        ),
                    ]
                )
                chain = prompt | llm
                doc_response = chain.invoke({"doc": doc_response.content})

        # Store both the raw response and ensure we have pure content
        raw_response = doc_response.content
        pure_document = raw_response
        document_explanation = ""

        # For markdown with code blocks, make sure we extract only the document
        # Unlike code generator, we keep all content but separate explanations
        if (
            "```" in raw_response
            and state["query"].document_format == DocumentFormat.MARKDOWN
        ):
            # For documents we want to preserve code blocks, but identify preamble
            parts = raw_response.split("\n")
            # Check if there's a preamble explanation before the actual document
            if (
                parts
                and not parts[0].startswith("#")
                and not parts[0].startswith("```")
            ):
                # Find where the actual document starts (first heading or code block)
                for i, line in enumerate(parts):
                    if line.startswith("#") or line.startswith("```"):
                        document_explanation = "\n".join(parts[:i]).strip()
                        pure_document = "\n".join(parts[i:]).strip()
                        break

        state["context"]["generated_document_raw"] = raw_response
        state["context"]["generated_document"] = pure_document
        state["context"]["document_explanation"] = document_explanation
        state["context"]["document_generation_completed"] = True
        logger.info(
            f"Document generation completed for {state['query'].document_format}"
        )
    except Exception as e:
        logger.error(f"Error in document generation: {str(e)}")
        state["context"]["document_generation_completed"] = False
        state["context"]["error"] = str(e)
    return state
