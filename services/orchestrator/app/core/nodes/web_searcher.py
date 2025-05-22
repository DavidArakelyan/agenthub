"""Web searcher node for workflow."""

import logging
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


async def web_searcher(state: AgentState) -> AgentState:
    """Performs web search based on the task requirements."""
    try:
        if not state["query"].needs_web_search:
            return state

        # Get the query from state
        query = state["query"].content

        # Call websearch service
        search_results = {
            "query": query,
            "results": [],
        }  # To be implemented with actual service call

        # Update state with search results
        state["context"]["web_search_results"] = search_results
        state["context"]["web_search_completed"] = True
        logger.info("Web search completed successfully")
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        state["context"]["web_search_completed"] = False
        state["context"]["error"] = str(e)
    return state
