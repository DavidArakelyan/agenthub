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


def validate_typescript_code(code: str) -> bool:
    """Validate TypeScript code for best practices and syntax."""
    validation_rules = [
        (r"\bvar\b", False, "Avoid using 'var', prefer 'let' or 'const'"),
        (
            r"function\s+\w+\s*\([^:)]*\)",
            False,
            "Functions should have type annotations",
        ),
        (r"(interface|type)\s+\w+", True, "Missing interface or type definition"),
        (r":\s*[A-Z]\w+(\[\])?", True, "Missing type annotations"),
        (
            r"React\.(FC|FunctionComponent)<",
            True,
            "React components should use TypeScript generics",
        ),
    ]

    issues = []
    for pattern, should_exist, message in validation_rules:
        matches = bool(re.search(pattern, code))
        if should_exist != matches:
            issues.append(message)

    return len(issues) == 0


def validate_markdown_syntax(content: str) -> bool:
    """Validate Markdown content for proper syntax and structure."""
    validation_rules = [
        (r"^#{1,6}\s.+$", True, "Headers should have space after #"),
        (r"```[\w]*\n[\s\S]*?\n```", True, "Code blocks should be properly formatted"),
        (r"\[([^\]]+)\]\(([^)]+)\)", True, "Links should have both text and target"),
        (r"^\s*[-*+]\s.+$", True, "Lists should be properly formatted"),
        (r"\|.+\|\n\|[-:|\s]+\|", True, "Tables should have header separators"),
    ]

    issues = []
    for pattern, should_exist, message in validation_rules:
        matches = bool(re.search(pattern, content, re.MULTILINE))
        if should_exist != matches:
            issues.append(message)

    return len(issues) == 0


async def code_generator(state: AgentState) -> AgentState:
    """Generates code in the specified programming language."""
    try:
        if (
            not isinstance(state["query"], ComplexQuery)
            or state["query"].code_language is None
        ):
            raise ValueError("Invalid state for code generation")

        if not state["query"].content.strip():
            raise ValueError("Empty query")

        llm = ChatOpenAI(
            temperature=settings.code_model_temperature,
            model_name=settings.code_model_name,
            openai_api_key=settings.openai_api_key,
        )

        # New detailed language-specific prompts
        language_prompts = {
            CodeLanguage.PYTHON: (
                "Generate Python code following these guidelines:\n"
                "1. Follow PEP 8 style guide\n"
                "2. Include detailed docstrings (Google style)\n"
                "3. Add type hints for function parameters\n"
                "4. Include error handling where appropriate\n"
                "5. Add comments for complex logic\n"
            ),
            CodeLanguage.TYPESCRIPT: (
                "Generate TypeScript code following these guidelines:\n"
                "1. Use strict type checking\n"
                "2. Follow Airbnb TypeScript style guide\n"
                "3. Include JSDoc comments\n"
                "4. Use async/await for asynchronous code\n"
                "5. Include error handling with try/catch\n"
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

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    language_prompts.get(
                        state["query"].code_language, "Write clean, documented code."
                    ),
                ),
                ("human", "Task: {input}"),
            ]
        )

        chain = prompt | llm
        code_response = chain.invoke({"input": state["query"].content})
        # Log the raw response
        logger.info(f"Raw LLM Response: {code_response}")
        logger.info(f"Raw LLM Response Content: {code_response.content}")

        # Add validation for TypeScript
        if state["query"].code_language == CodeLanguage.TYPESCRIPT:
            if not validate_typescript_code(code_response.content):
                logger.warning(
                    "Generated TypeScript code doesn't follow best practices"
                )
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
        state["context"]["generated_code"] = code_response.content
        state["context"]["code_generation_completed"] = True
        logger.info(f"Code generation completed for {state['query'].code_language}")
    except Exception as e:
        logger.error(f"Error in code generation: {str(e)}")
        state["context"]["code_generation_completed"] = False
        state["context"]["error"] = str(e)
    return state


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
        logger.info(f"Raw LLM Response: {doc_response}")
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

    """Handles complex queries by invoking the workflow."""
    try:
        state["current_step"] = "generator_type_classifier"
        return state
    except Exception as e:
        logger.error(f"Error in complex query handling: {str(e)}")
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

            # Use settings from config
            llm = ChatOpenAI(
                temperature=settings.main_model_temperature,
                model_name=settings.main_model_name,
                openai_api_key=settings.openai_api_key,
            )

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

            llm = ChatOpenAI(
                temperature=settings.main_model_temperature,
                model_name=settings.main_model_name,
                openai_api_key=settings.openai_api_key,
            )
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
                'Return JSON: {{"generator_type": "code" or "document"}}'
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

        def language_classifier(state: AgentState) -> AgentState:
            """Classify specific programming language for code generation."""
            logger.info("Classifying programming language...")
            if (
                not isinstance(state["query"], ComplexQuery)
                or state["query"].generator_type != GeneratorType.CODE
            ):
                return state

            llm = ChatOpenAI(
                temperature=settings.code_model_temperature,
                model_name=settings.code_model_name,
                openai_api_key=settings.openai_api_key,
            )
            system_prompt = (
                "You are a programming language classification agent. \n"
                "Analyze this query and determine the required programming language for the task.\n"
                "Consider the following languages:\n"
                "- Python (py)\n"
                "- Typescript (ts)\n"
                "- C++ (cpp)\n"
                "- Java (java)\n\n"
                "If user has specified a language, use that. Otherwise, classify based on the task.\n"
                "Determine the best programming language for this task:\n"
                "For example:\n"
                "Python (py):\n"
                "- Scripting and automation\n"
                "- Data processing and analysis\n"
                "- Web applications and APIs\n"
                "- Machine learning and AI\n\n"
                "Typescript (ts)\n"
                "- Web applications (frontend/backend)\n"
                "- Node.js applications\n"
                "- Type-safe JavaScript projects\n"
                "- Large-scale applications (frontend)\n\n"
                "C++ (cpp):\n"
                "- Performance-critical applications\n"
                "- Systems programming\n"
                "- Game development\n"
                "- Resource-constrained environments\n\n"
                "Java (java):\n"
                "- Enterprise applications\n"
                "- Android development\n"
                "- Large-scale systems (backend)\n"
                "- Cross-platform desktop apps\n\n"
                "If nothing is specified or nothing matches the description provided, return 'py' as default."
                'Return JSON: {{"language": "py" or "ts" or "cpp" or "java"}}'
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
            logger.info(f"Raw LLM Response (Language Classifier): {response}\n")
            logger.info(
                f"Raw LLM Response Content (Language Classifier): {response.content}\n"
            )

            # Parse the response content
            result = json.loads(response.content)
            # Update the state with the language information
            state["query"].code_language = CodeLanguage(result["language"])
            return state

        def format_classifier(state: AgentState) -> AgentState:
            """Classify specific document format for document generation."""
            logger.info("Classifying document format...")
            if (
                not isinstance(state["query"], ComplexQuery)
                or state["query"].generator_type != GeneratorType.DOCUMENT
            ):
                return state

            llm = ChatOpenAI(
                temperature=settings.document_model_temperature,
                model_name=settings.document_model_name,
                openai_api_key=settings.openai_api_key,
            )
            system_prompt = (
                "You are a document format classification agent. \n"
                "Analyze this query and determine the required document format for the task.\n"
                "Consider the following formats:\n"
                "- Text (txt): for plain text content\n"
                "- Markdown (md): for formatted text content\n"
                "- Doc (doc): for formatted documents\n"
                "- PDF (pdf): for formal documents and reports\n"
                "If user has specified a particular format, use that. Otherwise, classify based on the task.\n"
                "Determine the best document format for this content:\n"
                "Text (txt):\n"
                "- Simple, unformatted content\n"
                "- Simple readme files and notes\n"
                "- Configuration files\n"
                "- Quick documentation\n\n"
                "Markdown (md):\n"
                "- Documentation with formatting\n"
                "- README files with links\n"
                "- Content needing version control\n"
                "- Blogs and articles\n\n"
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
                'Return JSON: {{"format": "txt" or "md" or "doc" or "pdf"}}'
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
            logger.info(f"Raw LLM Response (Format Classifier): {response}\n")
            logger.info(
                f"Raw LLM Response Content (Format Classifier): {response.content}\n"
            )

            # Parse the response content
            result = json.loads(response.content)
            # Update the state with the format information
            state["query"].document_format = DocumentFormat(result["format"])
            return state

        def query_type_router_func(s):
            if isinstance((s["query"]), ComplexQuery):
                return "generator_type_classifier"
            return "response_generator"

        def generation_type_router_func(s):
            if s["query"].generator_type == GeneratorType.CODE:
                return "language_classifier"
            elif s["query"].generator_type == GeneratorType.DOCUMENT:
                return "format_classifier"
            return "response_generator"

        # Add nodes
        workflow.add_node("query_type_classifier", query_type_classifier)
        workflow.add_node("generator_type_classifier", generator_type_classifier)
        workflow.add_node("language_classifier", language_classifier)
        workflow.add_node("format_classifier", format_classifier)
        workflow.add_node("web_searcher", web_searcher)
        workflow.add_node("document_processor", document_processor)
        workflow.add_node("code_generator", code_generator)
        workflow.add_node("document_generator", document_generator)
        workflow.add_node("response_generator", response_generator)

        # Add cinditional edges
        workflow.add_conditional_edges("query_type_classifier", query_type_router_func)
        workflow.add_conditional_edges(
            "generator_type_classifier", generation_type_router_func
        )
        # Add explicit edges to corresponding generators
        workflow.add_edge("language_classifier", "code_generator")
        workflow.add_edge("format_classifier", "document_generator")

        # Direct edges to response generator
        workflow.add_edge("code_generator", "response_generator")
        workflow.add_edge("document_generator", "response_generator")

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
