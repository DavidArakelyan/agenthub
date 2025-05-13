"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from typing import Annotated, Any, Dict, List, TypedDict, Literal  # noqa: F401
from langgraph.graph import Graph, StateGraph
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import BaseMessage
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging

from app.core.config import get_settings
from app.core.mcp_client import mcp

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
    query_type: Literal["simple", "complex"]
    generation_type: Literal["code", "document", "none"]
    target_format: Literal["cpp", "py", "java", "txt", "doc", "pdf", "none"]


def create_agent_workflow() -> Graph:
    """
    Creates the main agent workflow using LangGraph.

    The workflow implements the Model Context Protocol and handles:
    1. Query Classification
    2. Task Planning
    3. Web Search (conditional)
    4. Document Processing (conditional)
    5. Code Generation (conditional)
    6. Document Generation (conditional)
    7. Response Generation
    """
    try:
        logger.info("Creating agent workflow")
        # Initialize the state graph
        workflow = StateGraph(AgentState)

        # Define the nodes (agents)
        def query_classifier(state: AgentState) -> AgentState:
            """Classifies the query as simple or complex and determines required processing."""
            llm = ChatOpenAI(
                temperature=settings.main_model_temperature,
                model_name=settings.main_model_name,
                openai_api_key=settings.openai_api_key,
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a query classification agent. Analyze the query and determine:\n"
                        "1. If it's a simple query (within LLM's knowledge, no code/doc generation, no context)\n"
                        "2. If it's a complex query (needs recent info, code/doc generation, or has context)\n"
                        "3. If it requires code generation (specify language: cpp, py, java)\n"
                        "4. If it requires document generation (specify format: txt, doc, pdf)\n"
                        "Return a JSON with the following structure:\n"
                        '{{\n'
                        '  "query_type": "simple" | "complex",\n'
                        '  "needs_web_search": boolean,\n'
                        '  "needs_document_processing": boolean,\n'
                        '  "generation_type": "code" | "document" | "none",\n'
                        '  "target_format": "cpp" | "py" | "java" | "txt" | "doc" | "pdf" | "none"\n'
                        "}}\n",
                    ),
                    ("human", "Query: {input}"),
                ]
            )
            chain = prompt | llm

            # Get the query from state
            query = state["messages"][-1].content

            # Initialize task status if not present
            if "task_status" not in state:
                state["task_status"] = {}

            # Classify query and parse the response
            classification = chain.invoke({"input": query})
            try:
                class_data = json.loads(classification.content)
                state["query_type"] = class_data.get("query_type", "simple")
                state["task_status"]["needs_web_search"] = class_data.get(
                    "needs_web_search", False
                )
                state["task_status"]["needs_document_processing"] = class_data.get(
                    "needs_document_processing", False
                )
                state["generation_type"] = class_data.get("generation_type", "none")
                state["target_format"] = class_data.get("target_format", "none")
            except json.JSONDecodeError:
                # Default to simple query if parsing fails
                state["query_type"] = "simple"
                state["task_status"]["needs_web_search"] = False
                state["task_status"]["needs_document_processing"] = False
                state["generation_type"] = "none"
                state["target_format"] = "none"

            return state

        def web_searcher(state: AgentState) -> AgentState:
            """Performs web search based on the task requirements."""
            try:
                # Get the query from state
                query = state["messages"][-1].content

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

        async def document_processor(state: AgentState) -> AgentState:
            """Processes and embeds documents for context."""
            try:
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
                    raise Exception(
                        f"Document processing failed: {process_response.error}"
                    )

                # Get the user's query from state
                query = state["messages"][-1].content

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
                logger.info(
                    "Document processing and semantic search completed successfully"
                )
            except Exception as e:
                logger.error(f"Error in document processing: {str(e)}")
                state["context"]["document_processed"] = False
                state["context"]["error"] = str(e)
            return state

        def code_generator(state: AgentState) -> AgentState:
            """Generates code in the specified programming language."""
            try:
                llm = ChatOpenAI(
                    temperature=settings.code_model_temperature,
                    model_name=settings.code_model_name,
                    openai_api_key=settings.openai_api_key,
                )

                language_prompts = {
                    "py": "Write Python code that is well-documented and follows PEP8.",
                    "cpp": "Write C++ code following modern C++17 practices with clear documentation.",
                    "java": "Write Java code following standard conventions with proper JavaDoc.",
                }

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            language_prompts.get(
                                state["target_format"], "Write clean, documented code."
                            ),
                        ),
                        ("human", "Task: {input}"),
                    ]
                )

                chain = prompt | llm

                # Generate code based on the last message and context
                code_response = chain.invoke(
                    {
                        "input": state["messages"][-1].content,
                    }
                )

                state["context"]["generated_code"] = code_response.content
                state["context"]["code_generation_completed"] = True
                logger.info(f"Code generation completed for {state['target_format']}")
            except Exception as e:
                logger.error(f"Error in code generation: {str(e)}")
                state["context"]["code_generation_completed"] = False
                state["context"]["error"] = str(e)
            return state

        def document_generator(state: AgentState) -> AgentState:
            """Generates documents in the specified format."""
            try:
                llm = ChatOpenAI(
                    temperature=settings.document_model_temperature,
                    model_name=settings.document_model_name,
                    openai_api_key=settings.openai_api_key,
                )

                format_prompts = {
                    "txt": "Generate plain text content that is clear and well-structured.",
                    "doc": "Generate content suitable for a Word document with proper formatting.",
                    "pdf": "Generate content suitable for a PDF document with clear sections.",
                }

                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            format_prompts.get(
                                state["target_format"],
                                "Generate well-structured content.",
                            ),
                        ),
                        ("human", "Task: {input}"),
                    ]
                )

                chain = prompt | llm

                # Generate document based on the last message and context
                doc_response = chain.invoke(
                    {
                        "input": state["messages"][-1].content,
                    }
                )

                state["context"]["generated_document"] = doc_response.content
                state["context"]["document_generation_completed"] = True
                logger.info(
                    f"Document generation completed for {state['target_format']}"
                )
            except Exception as e:
                logger.error(f"Error in document generation: {str(e)}")
                state["context"]["document_generation_completed"] = False
                state["context"]["error"] = str(e)
            return state

        def response_generator(state: AgentState) -> AgentState:
            """Generates the final response based on collected information."""
            llm = ChatOpenAI(
                temperature=settings.main_model_temperature,
                model_name=settings.main_model_name,
                openai_api_key=settings.openai_api_key,
            )

            # Prepare generated content for canvas if any
            if state["context"].get("generated_code"):
                state["context"]["canvas_content"] = {
                    "type": "code",
                    "format": state["target_format"],
                    "content": state["context"]["generated_code"],
                }
            elif state["context"].get("generated_document"):
                state["context"]["canvas_content"] = {
                    "type": "document",
                    "format": state["target_format"],
                    "content": state["context"]["generated_document"],
                }

            # Generate response using context
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are a helpful assistant that generates responses based on collected information. "
                        "If code or document was generated, reference it in your response.",
                    ),
                    ("human", "Input: {input}"),
                ]
            )
            chain = prompt | llm
            response = chain.invoke({"input": str(state["context"])})

            # Update state
            state["messages"].append(SystemMessage(content=str(response)))
            state["current_step"] = "end"
            return state

        # Add nodes to the graph
        workflow.add_node("query_classifier", query_classifier)
        workflow.add_node("web_searcher", web_searcher)
        workflow.add_node("document_processor", document_processor)
        workflow.add_node("code_generator", code_generator)
        workflow.add_node("document_generator", document_generator)
        workflow.add_node("response_generator", response_generator)

        # Define conditional edges
        def should_web_search(state: AgentState) -> bool:
            return state["task_status"].get("needs_web_search", False)

        def should_process_documents(state: AgentState) -> bool:
            return state["task_status"].get("needs_document_processing", False)

        def should_generate_code(state: AgentState) -> bool:
            return state["generation_type"] == "code"

        def should_generate_document(state: AgentState) -> bool:
            return state["generation_type"] == "document"

        def is_simple_query(state: AgentState) -> bool:
            return state["query_type"] == "simple"

        # Add edges with conditions
        workflow.add_conditional_edges(
            "query_classifier",
            {
                "web_searcher": should_web_search,
                "document_processor": should_process_documents,
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "response_generator": lambda state: (
                    is_simple_query(state)
                    or not any(
                        [
                            should_web_search(state),
                            should_process_documents(state),
                            should_generate_code(state),
                            should_generate_document(state),
                        ]
                    )
                ),
            },
        )

        # Add edges from all processors to response generator
        workflow.add_edge("web_searcher", "response_generator")
        workflow.add_edge("document_processor", "response_generator")
        workflow.add_edge("code_generator", "response_generator")
        workflow.add_edge("document_generator", "response_generator")

        # Set entry point
        workflow.set_entry_point("query_classifier")

        # Compile the graph
        return workflow.compile()
    except Exception as e:
        logger.error(f"Error creating agent workflow: {str(e)}")
        raise


def initialize_state(query: str) -> AgentState:
    """Initialize the agent state with a user query."""
    try:
        logger.info(f"Initializing state with message: {query}")
        return AgentState(
            messages=[HumanMessage(content=query)],
            current_step="start",
            task_status={},
            context={},
            query_type="simple",
            generation_type="none",
            target_format="none",
        )
    except Exception as e:
        logger.error(f"Error initializing state: {str(e)}")
        raise
