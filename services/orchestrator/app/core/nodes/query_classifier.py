"""Query type classifier node implementation."""

from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import json
import logging
import re
import os
import time

from ..config import get_settings
from ..types import SimpleQuery, ComplexQuery, GeneratorType, QueryAction

settings = get_settings()
logger = logging.getLogger(__name__)

# Store the most recent file identifier
_RECENT_IDENTIFIERS_FILE = os.path.join(os.path.dirname(__file__), '../../..', 'generated_content/recent_identifiers.json')

def _save_recent_identifier(file_identifier: str):
    """Save a file identifier as the most recent one."""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(_RECENT_IDENTIFIERS_FILE), exist_ok=True)
        
        # Load existing data or create new structure
        data = {}
        if os.path.exists(_RECENT_IDENTIFIERS_FILE):
            try:
                with open(_RECENT_IDENTIFIERS_FILE, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}
        
        # Update with new identifier
        data["last_identifier"] = file_identifier
        data["timestamp"] = time.time()
        
        # Keep track of recent identifiers (most recent first)
        recent_list = data.get("recent", [])
        if file_identifier in recent_list:
            recent_list.remove(file_identifier)
        recent_list.insert(0, file_identifier)
        # Keep only the 10 most recent
        data["recent"] = recent_list[:10]
        
        # Save the updated data
        with open(_RECENT_IDENTIFIERS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved recent file identifier: {file_identifier}")
    except Exception as e:
        logger.error(f"Error saving recent identifier: {str(e)}")

def _get_most_recent_identifier() -> str:
    """Get the most recently used file identifier."""
    try:
        if os.path.exists(_RECENT_IDENTIFIERS_FILE):
            with open(_RECENT_IDENTIFIERS_FILE, 'r') as f:
                data = json.load(f)
                if "last_identifier" in data:
                    logger.info(f"Retrieved most recent identifier: {data['last_identifier']}")
                    return data["last_identifier"]
    except Exception as e:
        logger.error(f"Error retrieving recent identifier: {str(e)}")
    
    # Return a fallback identifier if none is found
    fallback = f"recent_{int(time.time())}"
    logger.info(f"No recent identifier found, using fallback: {fallback}")
    return fallback

# ... existing code ...

def query_type_classifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """First level classification: Simple vs Complex and New vs Update"""
    logger.info("First level classification: Simple vs Complex and New vs Update...\n")

    # Use settings from config
    llm = ChatOpenAI(
        #temperature=settings.main_model_temperature,
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

    # First, check if this is an update query using pattern matching
    query_content = state["messages"][-1].content
    is_update_query = False
    file_identifier = None
    
    # Common patterns for update requests
    update_patterns = [
        r"update (?:the|this)? (.+?) (?:file|code|document)",
        r"modify (?:the|this)? (.+?) (?:file|code|document)",
        r"change (?:the|this)? (.+?) (?:file|code|document)",
        r"edit (?:the|this)? (.+?) (?:file|code|document)",
        r"revise (?:the|this)? (.+?) (?:file|code|document)",
        r"improve (?:the|this)? (.+?) (?:file|code|document)",
    ]
    
    for pattern in update_patterns:
        match = re.search(pattern, query_content, re.IGNORECASE)
        if match:
            is_update_query = True
            file_identifier = match.group(1).strip()
            logger.info(f"Update query detected. File identifier: {file_identifier}")
            break
    
    # If not detected by patterns, use LLM to classify if it's an update
    if not is_update_query:
        update_system_prompt = (
            "You are a query classification agent specializing in identifying update requests.\n"
            "Analyze if the query is asking to update or modify previously generated content.\n"
            "Examples of update requests:\n"
            "- 'Update the Python code you generated to include error handling'\n"
            "- 'Modify the documentation to add a new section'\n"
            "- 'Change the algorithm to be more efficient'\n"
            "- 'Add comments to the code you wrote'\n\n"
            "If this is an update request, try to identify which file or content needs to be updated.\n"
            "The file identifier might be directly mentioned in the query or inferred from context.\n"
            "If you can't determine a specific identifier, fall back to the most recently generated file_identifier.\n"
            'Return JSON: {{"is_update": boolean, "file_identifier": string or null}}'
        )
        update_prompt = ChatPromptTemplate.from_messages(
            [("system", update_system_prompt), ("human", "{query}")]
        )
        update_chain = update_prompt | llm
        update_response = update_chain.invoke({"query": query_content})
    
        # Parse the update classification
        update_result = json.loads(update_response.content)
        is_update_query = update_result.get("is_update", False)
        file_identifier = update_result.get("file_identifier", None)
        
        if is_update_query:
            logger.info(f"LLM classified as update query. File identifier: {file_identifier}")
            
    # If update query is detected but no file_identifier is found, 
            # use another LLM call to try harder to determine which content is being referenced
            if not file_identifier:
                # Try to get the most recent identifier
                most_recent = _get_most_recent_identifier()
                
                find_content_prompt = (
                    "You are an assistant helping to identify which previously generated content a user wants to update.\n"
                    "Analyze the update request carefully and extract any clues about which content the user is referring to.\n"
                    "Look for:\n"
                    "1. References to specific code or document functionality\n"
                    "2. References to file types or programming languages\n"
                    "3. References to topics or subjects that might be in a filename\n"
                    "4. Any other identifying information that could help match this to existing content\n\n"
                    "If you can't determine a specific identifier with high confidence, assume it's about the most recently generated content.\n"
                    "Based on the query, generate a possible file identifier that would match existing content.\n"
                    'Return JSON: {"possible_file_identifier": string}' #deliberately wrong to not generate a speculative identifier
                )
                find_content_chain = ChatPromptTemplate.from_messages(
                    [("system", find_content_prompt), ("human", "{query}")]
                ) | llm
                
                try:
                    find_content_response = find_content_chain.invoke({"query": query_content})
                    find_content_result = json.loads(find_content_response.content)
                    file_identifier = find_content_result.get("possible_file_identifier")
                    if file_identifier:
                        logger.info(f"Found possible file identifier for update query: {file_identifier}")
                    else:
                        # Fallback to the most recent identifier
                        file_identifier = most_recent
                        logger.info(f"Using most recent file identifier for update query: {file_identifier}")
                except Exception as e:
                    logger.error(f"Error finding content identifier: {str(e)}")
                    # Fallback to the most recent identifier on exception
                    file_identifier = most_recent
                    logger.info(f"Using most recent file identifier after error: {file_identifier}")

    # Now proceed with the regular classification
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
    response = chain.invoke({"query": query_content})
    
    # Log the raw response
    logger.debug(f"Raw LLM Response (Query Classifier): {response}\n")
    logger.debug(f"Raw LLM Response Content (Query Classifier): {response.content}\n")

    result = json.loads(response.content)

    # Set query action (new or update)
    query_action = QueryAction.UPDATE if is_update_query else QueryAction.NEW

    # Generate a file_identifier for new complex queries only
    if result["type"] == "complex" and not is_update_query and not file_identifier:
        # Use the LLM to generate a descriptive filename
        file_gen_system_prompt = (
            "You are a filename generator. Based on the query, generate a descriptive and "
            "filesystem-safe filename (no spaces, special characters) that represents the content. "
            "Do not include file extensions. Use only lowercase letters, numbers, and underscores. "
            "Keep it concise (max 30 chars) but descriptive."
            'Return JSON: {{"file_identifier": string}}'
        )
        file_gen_prompt = ChatPromptTemplate.from_messages(
            [("system", file_gen_system_prompt), ("human", "{query}")]
        )
        file_gen_chain = file_gen_prompt | llm
        try:
            file_gen_response = file_gen_chain.invoke({"query": query_content})
            file_gen_result = json.loads(file_gen_response.content)
            file_identifier = file_gen_result.get("file_identifier")
            logger.info(f"Generated file identifier for new query: {file_identifier}")
            
            # Save this as the most recent identifier
            if file_identifier:
                _save_recent_identifier(file_identifier)
        except Exception as e:
            logger.error(f"Error generating file identifier: {str(e)}")
            # Fallback to a generic identifier with timestamp
            import time
            import uuid
            file_identifier = f"generated_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            logger.info(f"Using fallback file identifier: {file_identifier}")
            
            # Save the fallback identifier too
            _save_recent_identifier(file_identifier)

    if result["type"] == "simple":
        state["query"] = SimpleQuery(
            content=query_content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
        )
    else:
        state["query"] = ComplexQuery(
            content=query_content,
            needs_web_search=result["needs_web_search"],
            needs_document_processing=result["needs_document_processing"],
            generator_type=existing_generator_type or GeneratorType.NONE,
            code_language=existing_code_language,
            document_format=existing_document_format,
            action=query_action,
            file_identifier=file_identifier,
            previous_content=None,  # Will be populated later if needed
        )

    # Save the most recent file identifier for new or updated queries
    if is_update_query or (result["type"] == "complex" and not existing_document_format):
        _save_recent_identifier(file_identifier)

    logger.info(f"Query type classification result: {result}")
    logger.info(f"Query type: {type(state['query'])}")
    if isinstance(state["query"], ComplexQuery):
        logger.info(f"Query action: {state['query'].action}")
        logger.info(f"File identifier: {state['query'].file_identifier}")
    
    return state
