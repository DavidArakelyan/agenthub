"""
Core workflow implementation using LangGraph for agent orchestration.
"""

from enum import Enum
from typing import Annotated, Any, Dict, List, TypedDict, Literal, Union, Optional  # noqa: F401
from pydantic import BaseModel
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


class GeneratorType(str, Enum):
    """Types of generators available in the system."""

    CODE = "code"
    DOCUMENT = "document"
    NONE = "none"


class CodeLanguage(str, Enum):
    """Supported programming languages."""

    PYTHON = "py"
    CPP = "cpp"
    JAVA = "java"


class DocumentFormat(str, Enum):
    """Supported document formats."""

    TEXT = "txt"
    DOC = "doc"
    PDF = "pdf"


class BaseQuery(BaseModel):
    """Base class for all query types."""

    content: str
    needs_web_search: bool = False
    needs_document_processing: bool = False


class SimpleQuery(BaseQuery):
    """Query that can be answered directly without generation."""

    pass


class ComplexQuery(BaseQuery):
    """Query that requires code or document generation."""

    generator_type: GeneratorType = GeneratorType.NONE
    code_language: Optional[CodeLanguage] = None
    document_format: Optional[DocumentFormat] = None


class AgentState(TypedDict):
    """State definition for the agent workflow."""

    messages: List[BaseMessage]
    current_step: str
    task_status: Dict[str, Any]
    context: Dict[str, Any]
    query: Union[SimpleQuery, ComplexQuery]  # New unified query model


def query_type_classifier(state: AgentState) -> AgentState:
    """First level classification: Simple vs Complex"""
    # If generation_type and target_format are already set, respect them
    if (
        isinstance(state["query"], ComplexQuery)
        and state["query"].generator_type != GeneratorType.NONE
    ):
        logger.info("Using existing query configuration")
        return state

    llm = ChatOpenAI(temperature=0.2, model_name=settings.main_model_name)

    # Old prompt preserved for reference
    # prompt = ChatPromptTemplate.from_messages([
    #     (
    #         "system",
    #         "You are a query classification agent. Analyze the query and determine:\n"
    #         "1. If it's a simple query (within LLM's knowledge, no code/doc generation, no context)\n"
    #         "2. If it's a complex query (needs recent info, code/doc generation, or has context)\n"
    #         "3. If it requires code generation (specify language: cpp, py, java)\n"
    #         "4. If it requires document generation (specify format: txt, doc, pdf)\n"
    #         "Return a JSON with the following structure:\n"
    #         '{{\n'
    #         '  "query_type": "simple" | "complex",\n'
    #         '  "needs_web_search": boolean,\n'
    #         '  "needs_document_processing": boolean,\n'
    #         '  "generation_type": "code" | "document" | "none",\n'
    #         '  "target_format": "cpp" | "py" | "java" | "txt" | "doc" | "pdf" | "none"\n'
    #         "}}\n",
    #     ),
    #     ("human", "Query: {input}"),
    # ])

    # New hierarchical classification prompt - fixed template variables
    system_prompt = (
        "Analyze if this query requires generation (code/document) or can be answered directly.\n"
        "A query is complex if it requires:\n"
        "1. Code generation\n"
        "2. Document generation\n"
        "3. Recent information from web search\n"
        "4. Processing existing documents\n\n"
        "Return JSON with the structure:\n"
        "{\n"
        '  "type": "simple" or "complex",\n'
        '  "needs_web_search": boolean,\n'
        '  "needs_document_processing": boolean\n'
        "}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{input}")]
    )

    chain = prompt | llm
    result = json.loads(chain.invoke({"input": state["messages"][-1].content}))

    if result["type"] == "simple":
        state["query"] = SimpleQuery(
            content=state["messages"][-1].content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
        )
    else:
        # Just mark as complex, details will be filled by generator_classifier
        state["query"] = ComplexQuery(
            content=state["messages"][-1].content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
        )
    return state


def generator_type_classifier(state: AgentState) -> AgentState:
    """Second level: Classify between Code vs Document generation"""
    if not isinstance(state["query"], ComplexQuery):
        return state

    llm = ChatOpenAI(temperature=0.2, model_name=settings.main_model_name)

    # Old prompt preserved for reference
    # prompt = ChatPromptTemplate.from_messages([
    #     (
    #         "system",
    #         "You are a code generation agent. Determine if this query needs:\n"
    #         "1. Code generation (with specific language)\n"
    #         "2. Document generation (with specific format)\n"
    #         "Return JSON with structure:\n"
    #         "{\n"
    #         '  "generation_type": "code" | "document" | "none",\n'
    #         '  "target_format": "cpp" | "py" | "java" | "txt" | "doc" | "pdf" | "none"\n'
    #         "}"
    #     ),
    #     ("human", "{query}")
    # ])

    # New generator type classification prompt
    system_prompt = (
        "Determine if this query needs code or document generation.\n"
        "Code generation is needed for:\n"
        "- Writing functions, classes, or programs\n"
        "- Implementing algorithms or data structures\n"
        "- Creating scripts or applications\n\n"
        "Document generation is needed for:\n"
        "- Creating documentation or reports\n"
        "- Generating formatted text content\n"
        "- Producing structured documents\n\n"
        'Return JSON: {"generator_type": "code" or "document"}'
    )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{input}")]
    )

    chain = prompt | llm
    result = json.loads(chain.invoke({"input": state["query"].content}))
    state["query"].generator_type = GeneratorType(result["generator_type"])
    return state


def format_classifier(state: AgentState) -> AgentState:
    """Third level: Classify specific language/format"""
    if not isinstance(state["query"], ComplexQuery):
        return state

    llm = ChatOpenAI(temperature=0.2, model_name=settings.main_model_name)

    if state["query"].generator_type == GeneratorType.CODE:
        # Old code language prompt preserved for reference
        # prompt = ChatPromptTemplate.from_messages([
        #     (
        #         "system",
        #         "Select the most appropriate programming language:\n"
        #         "- Python (py): for scripting, data processing, web backends\n"
        #         "- C++ (cpp): for systems programming, performance-critical code\n"
        #         "- Java (java): for enterprise applications, Android development\n"
        #         'Return JSON: {"language": "py" | "cpp" | "java"}'
        #     ),
        #     ("human", "{query}")
        # ])

        # New code language classification prompt
        system_prompt = (
            "Determine the best programming language for this task:\n"
            "Python (py):\n"
            "- Scripting and automation\n"
            "- Data processing and analysis\n"
            "- Web applications and APIs\n"
            "- Machine learning and AI\n\n"
            "C++ (cpp):\n"
            "- Performance-critical applications\n"
            "- Systems programming\n"
            "- Game development\n"
            "- Resource-constrained environments\n\n"
            "Java (java):\n"
            "- Enterprise applications\n"
            "- Android development\n"
            "- Large-scale systems\n"
            "- Cross-platform desktop apps\n\n"
            'Return JSON: {"language": "py" or "cpp" or "java"}'
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", "{input}")]
        )
        chain = prompt | llm
        result = json.loads(chain.invoke({"input": state["query"].content}))
        state["query"].code_language = CodeLanguage(result["language"])

    elif state["query"].generator_type == GeneratorType.DOCUMENT:
        # Old document format prompt preserved for reference
        # prompt = ChatPromptTemplate.from_messages([
        #     (
        #         "system",
        #         "Select the most appropriate document format:\n"
        #         "- Text (txt): for plain text content\n"
        #         "- Doc (doc): for formatted documents\n"
        #         "- PDF (pdf): for formal documents and reports\n"
        #         'Return JSON: {"format": "txt" | "doc" | "pdf"}'
        #     ),
        #     ("human", "{query}")
        # ])

        # New document format classification prompt
        system_prompt = (
            "Determine the best document format for this content:\n"
            "Text (txt):\n"
            "- Simple, unformatted content\n"
            "- README files and notes\n"
            "- Configuration files\n"
            "- Quick documentation\n\n"
            "Word Document (doc):\n"
            "- Formatted text with styles\n"
            "- Documents needing revision\n"
            "- Interactive content\n"
            "- Collaborative editing\n\n"
            "PDF (pdf):\n"
            "- Final documentation\n"
            "- Formal reports\n"
            "- Print-ready documents\n"
            "- Long-term archival\n\n"
            'Return JSON: {"format": "txt" or "doc" or "pdf"}'
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", "{input}")]
        )
        chain = prompt | llm
        result = json.loads(chain.invoke({"input": state["query"].content}))
        state["query"].document_format = DocumentFormat(result["format"])

    return state


def web_searcher(state: AgentState) -> AgentState:
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


def code_generator(state: AgentState) -> AgentState:
    """Generates code in the specified programming language."""
    try:
        if not isinstance(state["query"], ComplexQuery):
            raise ValueError("Invalid query type for code generation")

        if state["query"].generator_type != GeneratorType.CODE:
            raise ValueError("Query is not configured for code generation")

        if not isinstance(state["query"].code_language, CodeLanguage):
            raise ValueError(
                f"Invalid language specified: {state['query'].code_language}"
            )

        if not state["query"].content.strip():
            raise ValueError("Empty query")

        llm = ChatOpenAI(
            temperature=settings.code_model_temperature,
            model_name=settings.code_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # Language-specific prompts
        language_prompts = {
            CodeLanguage.PYTHON: (
                "Generate Python code following these guidelines:\n"
                "1. Follow PEP 8 style guide\n"
                "2. Include detailed docstrings (Google style)\n"
                "3. Add type hints for function parameters\n"
                "4. Include error handling where appropriate\n"
                "5. Add comments for complex logic\n"
            ),
            CodeLanguage.CPP: (
                "Generate C++ code following these guidelines:\n"
                "1. Use modern C++17 features\n"
                "2. Follow Google C++ style guide\n"
                "3. Include proper memory management\n"
                "4. Add comprehensive error handling\n"
                "5. Document public interfaces\n"
            ),
            CodeLanguage.JAVA: (
                "Generate Java code following these guidelines:\n"
                "1. Follow Oracle Java code conventions\n"
                "2. Include JavaDoc comments\n"
                "3. Use appropriate access modifiers\n"
                "4. Implement proper exception handling\n"
                "5. Follow SOLID principles\n"
            ),
        }

        # Get language-specific prompt or raise error
        language_prompt = language_prompts.get(state["query"].code_language)
        if not language_prompt:
            raise ValueError(f"Unsupported language: {state['query'].code_language}")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", language_prompt),
                (
                    "human",
                    "Task: {input}\n\nProvide ONLY the code without any additional explanation.",
                ),
            ]
        )

        chain = prompt | llm
        code_response = chain.invoke({"input": state["query"].content})

        state["context"]["generated_code"] = code_response.content
        state["context"]["code_generation_completed"] = True
        state["context"]["error"] = None
        logger.info(f"Code generation completed for {state['query'].code_language}")
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}")
        state["context"]["code_generation_completed"] = False
        state["context"]["generated_code"] = None
        state["context"]["error"] = str(e)
    return state


def document_generator(state: AgentState) -> AgentState:
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

        # Old format prompts preserved for reference
        # format_prompts = {
        #     "txt": "Generate plain text content that is clear and well-structured.",
        #     "doc": "Generate content suitable for a Word document with proper formatting.",
        #     "pdf": "Generate content suitable for a PDF document with clear sections.",
        # }

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

        state["context"]["generated_document"] = doc_response.content
        state["context"]["document_generation_completed"] = True
        logger.info(
            f"Document generation completed for {state['query'].document_format}"
        )
    except Exception as e:
        logger.error(f"Error in document generation: {str(e)}")
        state["context"]["document_generation_completed"] = False
        state["context"]["error"] = str(e)
    return state


def response_generator(state: AgentState) -> AgentState:
    """Generates the final response based on collected information."""
    try:
        llm = ChatOpenAI(
            temperature=settings.main_model_temperature,
            model_name=settings.main_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # Old response generation prompt preserved for reference
        # prompt = ChatPromptTemplate.from_messages([
        #     (
        #         "system",
        #         "You are a helpful assistant that generates responses based on collected information. "
        #         "If code or document was generated, reference it in your response.",
        #     ),
        #     ("human", "Input: {input}"),
        # ])

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
                    ("human", "Context: {context}\nProvide a comprehensive answer."),
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

        chain = prompt | llm
        response = chain.invoke({"context": str(state["context"])})

        # Update state
        state["messages"].append(SystemMessage(content=str(response)))
        state["current_step"] = "end"
        return state
    except Exception as e:
        logger.error(f"Error in response generation: {str(e)}")
        state["context"]["error"] = str(e)
        return state


def create_agent_workflow() -> Graph:
    """Creates the main agent workflow using LangGraph."""
    try:
        logger.info("Creating agent workflow")
        workflow = StateGraph(AgentState)

        # Add nodes to the graph
        workflow.add_node("query_type_classifier", query_type_classifier)
        workflow.add_node("generator_type_classifier", generator_type_classifier)
        workflow.add_node("format_classifier", format_classifier)
        workflow.add_node("web_searcher", web_searcher)
        workflow.add_node("document_processor", document_processor)
        workflow.add_node("code_generator", code_generator)
        workflow.add_node("document_generator", document_generator)
        workflow.add_node("response_generator", response_generator)
        workflow.add_node(
            "entry_router", lambda x: x
        )  # Pass-through node for initial routing

        # Define routing conditions
        def needs_classification(state: AgentState) -> bool:
            if isinstance(state["query"], ComplexQuery):
                return state["query"].generator_type == GeneratorType.NONE
            return True

        def needs_format_classification(state: AgentState) -> bool:
            if not isinstance(state["query"], ComplexQuery):
                return False
            if state["query"].generator_type == GeneratorType.CODE:
                return state["query"].code_language is None
            if state["query"].generator_type == GeneratorType.DOCUMENT:
                return state["query"].document_format is None
            return False

        def should_web_search(state: AgentState) -> bool:
            return state["query"].needs_web_search

        def should_process_documents(state: AgentState) -> bool:
            return state["query"].needs_document_processing

        def should_generate_code(state: AgentState) -> bool:
            return (
                isinstance(state["query"], ComplexQuery)
                and state["query"].generator_type == GeneratorType.CODE
                and state["query"].code_language is not None
            )

        def should_generate_document(state: AgentState) -> bool:
            return (
                isinstance(state["query"], ComplexQuery)
                and state["query"].generator_type == GeneratorType.DOCUMENT
                and state["query"].document_format is not None
            )

        def is_simple_query(state: AgentState) -> bool:
            return isinstance(state["query"], SimpleQuery)

        # Entry point routing
        workflow.add_conditional_edges(
            "entry_router",
            {
                # Route to appropriate classifier or directly to generator
                "query_type_classifier": needs_classification,
                "generator_type_classifier": lambda s: (
                    isinstance(s["query"], ComplexQuery)
                    and s["query"].generator_type != GeneratorType.NONE
                    and needs_format_classification(s)
                ),
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "web_searcher": should_web_search,
                "document_processor": should_process_documents,
                "response_generator": lambda s: not any(
                    [
                        needs_classification(s),
                        needs_format_classification(s),
                        should_generate_code(s),
                        should_generate_document(s),
                        should_web_search(s),
                        should_process_documents(s),
                    ]
                ),
            },
        )

        # Query type classifier routing
        workflow.add_conditional_edges(
            "query_type_classifier",
            {
                "generator_type_classifier": lambda s: not is_simple_query(s),
                "web_searcher": lambda s: is_simple_query(s) and should_web_search(s),
                "document_processor": lambda s: is_simple_query(s)
                and should_process_documents(s),
                "response_generator": lambda s: is_simple_query(s)
                and not (should_web_search(s) or should_process_documents(s)),
            },
        )

        # Generator type classifier routing
        workflow.add_conditional_edges(
            "generator_type_classifier",
            {
                "format_classifier": needs_format_classification,
                "web_searcher": should_web_search,
                "document_processor": should_process_documents,
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "response_generator": lambda s: not any(
                    [
                        needs_format_classification(s),
                        should_web_search(s),
                        should_process_documents(s),
                        should_generate_code(s),
                        should_generate_document(s),
                    ]
                ),
            },
        )

        # Format classifier routing
        workflow.add_conditional_edges(
            "format_classifier",
            {
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "web_searcher": should_web_search,
                "document_processor": should_process_documents,
                "response_generator": lambda s: not any(
                    [
                        should_generate_code(s),
                        should_generate_document(s),
                        should_web_search(s),
                        should_process_documents(s),
                    ]
                ),
            },
        )

        # Processing nodes routing
        workflow.add_conditional_edges(
            "web_searcher",
            {
                "document_processor": should_process_documents,
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "response_generator": lambda s: not any(
                    [
                        should_process_documents(s),
                        should_generate_code(s),
                        should_generate_document(s),
                    ]
                ),
            },
        )

        workflow.add_conditional_edges(
            "document_processor",
            {
                "code_generator": should_generate_code,
                "document_generator": should_generate_document,
                "response_generator": lambda s: not any(
                    [should_generate_code(s), should_generate_document(s)]
                ),
            },
        )

        # Generator nodes to response
        workflow.add_edge("code_generator", "response_generator")
        workflow.add_edge("document_generator", "response_generator")

        # Set entry point
        workflow.set_entry_point("entry_router")

        return workflow.compile()
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
            "task_status": {
                "classification_done": False,
                "web_search_done": False,
                "document_processing_done": False,
                "generation_done": False,
                "response_done": False,
            },
            "context": {
                "code_generation_completed": False,
                "document_generation_completed": False,
                "web_search_completed": False,
                "document_processed": False,
                "error": None,
                "generated_code": None,
                "generated_document": None,
                "web_search_results": None,
                "document_results": None,
                "canvas_content": None,
            },
            "query": SimpleQuery(content=query),
        }
        logger.info("Successfully initialized agent state")
        return state
    except Exception as e:
        logger.error(f"Error initializing agent state: {str(e)}")
        raise
