"""Web searcher node for workflow."""

import logging
from app.core.config import get_settings
from app.core.types import AgentState

logger = logging.getLogger(__name__)
settings = get_settings()


def sync_web_searcher(state: AgentState) -> AgentState:
    """
    Synchronous wrapper for web searcher.
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
        # Run the async web searcher
        return loop.run_until_complete(web_searcher(state))
    finally:
        # Only close the loop if we created it
        if should_close_loop:
            loop.close()


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
