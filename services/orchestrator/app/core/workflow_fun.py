from langgraph.graph import Graph, StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from typing import TypedDict, List, Literal, Dict
import logging
import traceback

from app.core.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


class AgentState(TypedDict):
    """State definition for the agent workflow."""

    messages: List[HumanMessage | SystemMessage]
    next: str | None


def create_initial_state(query: str) -> AgentState:
    """Create the initial state from a query."""
    return AgentState(messages=[HumanMessage(content=query)], next=None)


def sentiment_classifier(state: AgentState) -> AgentState:
    """Classify the sentiment of the query."""
    logger.info("Classifying sentiment of the query...")
    query = state["messages"][-1].content.lower()

    if any(word in query for word in ["fun", "interesting", "exciting"]):
        logger.info("Sentiment classified as: fun")
        state["next"] = "fun"
    else:
        logger.info("Sentiment classified as: regular")
        state["next"] = "regular"

    return state


def generate_response(state: AgentState) -> AgentState:
    """Generate response based on sentiment."""
    try:
        is_fun = state["next"] == "fun"
        temperature = 0.9 if is_fun else 0.7
        prompt_prefix = (
            "Respond in a fun and exciting way: "
            if is_fun
            else "Respond in a regular and informative way: "
        )

        llm = ChatOpenAI(
            temperature=temperature,
            model_name="gpt-3.5-turbo",
            openai_api_key=settings.openai_api_key,
        )

        input_message = prompt_prefix + state["messages"][-1].content
        logger.info(f"Sending message to OpenAI: {input_message}")

        response = llm.invoke([HumanMessage(content=input_message)])
        logger.info(f"Got response from OpenAI: {response.content}")

        state["messages"].append(SystemMessage(content=response.content))
        state["next"] = "end"

    except Exception as e:
        logger.error(f"Error in generate_response: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        state["messages"].append(SystemMessage(content=f"Error: {str(e)}"))
        state["next"] = "end"

    return state


def should_end(state: AgentState) -> bool:
    """Determine if the workflow should end."""
    return state["next"] == "end"


def create_fun_workflow() -> Graph:
    """Creates a simple workflow based on query sentiment."""
    logger.info("Creating the fun workflow...")

    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("sentiment_classifier", sentiment_classifier)
    workflow.add_node("generate_response", generate_response)

    # Add edges
    workflow.set_entry_point("sentiment_classifier")
    workflow.add_edge("sentiment_classifier", "generate_response")

    # Add conditional edge to end
    workflow.add_conditional_edges("generate_response", {END: should_end})

    return workflow.compile()


# Example usage
if __name__ == "__main__":
    query = "What is photosynthesis?"  # Changed to a regular query
    state = create_initial_state(query)
    workflow = create_fun_workflow()
    logger.info(f"Starting workflow execution with state: {state}")
    result = workflow.invoke(state)
    logger.info(f"Workflow execution completed. Final state: {result}")
    print("\nFinal response:")
    if len(result["messages"]) > 1:
        print(result["messages"][-1].content)
    else:
        print("No response generated")
