"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Annotated, Any, Dict, List, TypedDict, Literal, Union, Optional  # noqa: F401
from langgraph.graph import Graph, StateGraph
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging
import re

from app.core.config import get_settings
from app.core.mcp_client import mcp
from app.core.query import (
    GeneratorType,
    CodeLanguage,
    DocumentFormat,
    SimpleQuery,
    ComplexQuery,
)

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State definition for the agent workflow."""

    messages: List[BaseMessage]
    current_step: str
    task_status: Dict[str, Any]
    context: Dict[str, Any]
    query: Union[SimpleQuery, ComplexQuery]


def response_generator(state: AgentState) -> AgentState:
    """Generates the final response based on collected information."""
    logger.info("Invoking Responce Generator\n")
    logger.info(f"Invoking Responce Generator with the state {state}\n")

    try:
        llm = ChatOpenAI(
            temperature=settings.main_model_temperature,
            model_name=settings.main_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # New context-aware response generation prompt
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
            # For simple queries, include the query in the prompt
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
                state["context"]["canvas_content"] = {
                    "type": "code",
                    "format": state["query"].code_language,
                    "content": state["context"].get("generated_code", ""),
                }
            elif state["query"].generator_type == GeneratorType.DOCUMENT:
                state["context"]["canvas_content"] = {
                    "type": "document",
                    "format": state["query"].document_format,
                    "content": state["context"].get("generated_document", ""),
                }

        # Pass both query and context to the chain
        chain = prompt | llm
        response = chain.invoke(
            {"query": state["query"].content, "context": str(state["context"])}
        )

        # Log the raw response
        logger.info(f"Raw LLM Response: {response}\n")
        logger.info(f"Raw LLM Response Content: {response.content}\n")

        # Update state with just the content of the response
        state["messages"].append(SystemMessage(content=response.content))
        state["current_step"] = "end"
        return state
    except Exception as e:
        logger.error(f"Error in response generation: {str(e)}")
        state["context"]["error"] = str(e)
        return state


class AgentWorkflow:
    """Workflow implementation using LangGraph."""

    def __init__(self):
        """Initialize the workflow."""
        self.workflow = create_agent_workflow()

    async def ainvoke(self, state):
        """Invoke the workflow asynchronously."""
        try:
            logger.info(f"Processing state: {state}")
            # Execute the workflow
            result = await self.workflow.ainvoke(state)
            logger.info(f"Workflow completed with result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            return {
                "context": {
                    "code_generation_completed": False,
                    "document_generation_completed": False,
                    "error": str(e),
                }
            }


def create_agent_workflow() -> Graph:
    """Creates the main agent workflow using LangGraph."""
    logger.info("Creating the main agent workflow using LangGraph...\n")
    try:
        workflow = StateGraph(AgentState)

        def query_type_classifier(state: AgentState) -> AgentState:
            """First level classification: Simple vs Complex"""
            logger.info("First level classification: Simple vs Complex...\n")
            llm = ChatOpenAI(temperature=0.2, model_name=settings.main_model_name)

            # Preserve existing generator type and language/format if already set
            existing_generator_type = None
            existing_code_language = None
            existing_document_format = None

            if isinstance(state["query"], ComplexQuery):
                existing_generator_type = state["query"].generator_type
                existing_code_language = state["query"].code_language
                existing_document_format = state["query"].document_format

            system_prompt = (
                "You are a query classification agent. \n"
                "Classify if this query requires generation (code/document) or can be answered directly.\n"
                "Analyze the query and determine:\n"
                "1. If it's a simple query (no code or document generation requested): set 'type' in Response JSON to 'simple'\n"
                "2. If it's a complex query (needs code/doc generation): set 'type' in Response JSON to 'complex'\n"
                "3. Determine if it needs web search (needs recent info, past cutoff date): set 'needs_web_search' boolean\n"
                "4. Determine if it needs document processing (has additional context): set 'needs_document_processing' boolean\n"
                'Return JSON: {{"type": "simple" or "complex", "needs_web_search": boolean, "needs_document_processing": boolean}}'
            )
            prompt = ChatPromptTemplate.from_messages(
                [("system", system_prompt), ("human", "{query}")]
            )
            chain = prompt | llm
            response = chain.invoke({"query": state["messages"][-1].content})
            # Log the raw response
            logger.info(f"Raw LLM Response (Query Classifier): {response}\n")
            logger.info(
                f"Raw LLM Response Content (Query Classifier): {response.content}\n"
            )
            result = json.loads(response.content)

            if result["type"] == "simple":
                state["query"] = SimpleQuery(
                    content=state["messages"][-1].content,
                    needs_web_search=result["needs_web_search"],
                    needs_document_processing=result["needs_document_processing"],
                )
            else:
                state["query"] = ComplexQuery(
                    content=state["messages"][-1].content,
                    needs_web_search=result["needs_web_search"],
                    needs_document_processing=result["needs_document_processing"],
                    generator_type=existing_generator_type or GeneratorType.NONE,
                    code_language=existing_code_language,
                    document_format=existing_document_format,
                )
                # Add debug logging before return

            logger.debug(f"Query type classification result: {result}")
            logger.debug(f"Query type: {type(state['query'])}")
            return state

        def generator_type_classifier(state: AgentState) -> AgentState:
            """Second level: Classify between Code vs Document generation"""
            logger.info(
                "Second level: Classify between Code vs Document generation...\n"
            )
            # Add entry logging
            logger.info("Entering generator_type_classifier")
            logger.debug(f"State entering generator_type_classifier: {state}")
            if not isinstance(state["query"], ComplexQuery):
                return state

            llm = ChatOpenAI(temperature=0.2, model_name=settings.main_model_name)
            system_prompt = (
                "You are a classification agent determining the type of generation required. \n"
                "Analyze this query and determine if it needs code or document generation.\n"
                "Code generation is needed for:\n"
                "- Writing functions, classes, or programs\n"
                "- Implementing algorithms or data structures\n"
                "- Creating scripts or applications\n\n"
                "Document generation is needed for:\n"
                "- Creating documentation or reports\n"
                "- Generating formatted text content\n"
                "- Producing structured documents\n\n"
                'Return JSON: {{"generator_type": "code" or "document"}}',
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
            logger.info(f"Raw LLM Response (Generation Type Classifier): {response}\n")
            logger.info(
                f"Raw LLM Response Content (Generation Type Classifier): {response.content}\n"
            )
            # Parse the response content
            result = json.loads(response.content)  # Get the content first
            # Update the state with the generator type
            state["query"].generator_type = GeneratorType(result["generator_type"])
            return state

        def is_complex_query(s):
            result = isinstance(s["query"], ComplexQuery)
            logger.info(f"Edge condition - is_complex_query: {result}")
            return result

        def is_simple_query(s):
            result = isinstance(s["query"], SimpleQuery)
            logger.info(f"Edge condition - is_simple_query: {result}")
            return result

        # Add nodes
        workflow.add_node("query_type_classifier", query_type_classifier)
        workflow.add_node("generator_type_classifier", generator_type_classifier)
        workflow.add_node("response_generator", response_generator)

        # Add edges
        workflow.add_conditional_edges(
            "query_type_classifier",
            {
                "generator_type_classifier": is_complex_query,
                "response_generator": is_simple_query,
            },
        )

        workflow.add_edge("generator_type_classifier", "response_generator")

        # Set entry point
        workflow.set_entry_point("query_type_classifier")
        graph = workflow.compile()

        return graph

    except Exception as e:
        logger.error(f"Error creating agent workflow: {str(e)}")
        raise


def initialize_state(query: str) -> AgentState:
    """Initialize the agent state with a user query."""
    try:
        logger.info(f"Initializing agent state with query: {query}")
        state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "current_step": "start",
            "task_status": {},  # Empty dict to be populated by query classifier
            "context": {
                "code_generation_completed": False,
                "document_generation_completed": False,
                "web_search_completed": False,
                "document_processed": False,
                "error": None,
            },
            "query": SimpleQuery(content=query),  # Default to simple query
        }
        logger.info("Successfully initialized agent state")
        return state
    except Exception as e:
        logger.error(f"Error initializing agent state: {str(e)}")
        raise
