"""Document processor node for workflow."""

import logging
from app.core.mcp_client import mcp
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


async def document_processor(state: AgentState) -> AgentState:
    """Processes and embeds documents for context."""
    try:
        if not state["query"].needs_document_processing:
            return state

        # Get document path from context
        file_path = state["context"].get("document_path")
        metadata = state["context"].get("document_metadata", {})

        if not file_path:
            raise ValueError("No document path provided in context")

        # Call document service via FastMCP to process document
        process_response = await mcp.call(
            service="document-service",
            method="process_document",
            data={"file_path": file_path, "metadata": metadata},
        )

        if not process_response.success:
            raise Exception(f"Document processing failed: {process_response.error}")

        # Get the user's query from state
        query = state["query"].content

        # Perform semantic search to find relevant content
        search_response = await mcp.call(
            service="document-service",
            method="semantic_search",
            data={"query": query, "k": 4},  # Get top 4 most relevant chunks
        )

        if not search_response.success:
            raise Exception(f"Semantic search failed: {search_response.error}")

        # Update state with processing results and relevant content
        state["context"]["document_processed"] = True
        state["context"]["processing_result"] = process_response.data["message"]
        state["context"]["relevant_content"] = search_response.data["documents"]
        logger.info("Document processing and semantic search completed successfully")
    except Exception as e:
        logger.error(f"Error in document processing: {str(e)}")
        state["context"]["document_processed"] = False
        state["context"]["error"] = str(e)
    return state
