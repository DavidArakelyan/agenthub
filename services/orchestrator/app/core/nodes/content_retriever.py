"""Content retriever node for workflow.

This node is responsible for retrieving previous content for update queries.
"""

import logging
from typing import Dict, Any
import os
import json
import time
from app.core.types import ComplexQuery, QueryAction
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Use the existing generated_content directory in the project
CONTENT_STORE_PATH = os.path.join(os.path.dirname(__file__), '../../..', 'generated_content/data')


def ensure_store_exists():
    """Ensure the content store directory exists."""
    if not os.path.exists(CONTENT_STORE_PATH):
        os.makedirs(CONTENT_STORE_PATH, exist_ok=True)


def save_generated_content(file_id: str, content: str, metadata: Dict[str, Any] = None, is_update: bool = False):
    """Save generated content to the store for future retrieval."""
    ensure_store_exists()
    
    # Normalize file_id to be filesystem-safe
    safe_id = "".join(c if c.isalnum() else "_" for c in file_id)
    file_path = os.path.join(CONTENT_STORE_PATH, f"{safe_id}.json")
    
    # Initialize with current metadata
    current_metadata = metadata or {}
    current_time = current_metadata.get("timestamp", time.time())
    current_query = current_metadata.get("query", "")
    
    # For updates, try to load existing metadata first
    existing_data = {}
    if is_update and os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
            
            # Get existing metadata
            existing_metadata = existing_data.get("metadata", {})
            
            # Preserve created_at timestamp from original metadata
            if "created_at" in existing_metadata:
                current_metadata["created_at"] = existing_metadata["created_at"]
            else:
                current_metadata["created_at"] = existing_metadata.get("timestamp", current_time)
            
            # Track query history
            query_history = existing_metadata.get("query_history", [])
            if current_query and current_query not in query_history:
                query_history.append(current_query)
                current_metadata["query_history"] = query_history
                
            # Preserve other important metadata if not explicitly overwritten
            for key, value in existing_metadata.items():
                if key not in current_metadata and key not in ["timestamp", "query", "query_history"]:
                    current_metadata[key] = value
        except Exception as e:
            logger.error(f"Error reading existing metadata: {str(e)}")
    else:
        # For new content, initialize metadata
        current_metadata["created_at"] = current_time
        if current_query:
            current_metadata["query_history"] = [current_query]
    
    # Update the timestamp to current time
    current_metadata["timestamp"] = current_time
    
    # Create the content data with all metadata
    content_data = {
        "content": content,
        "metadata": current_metadata
    }
    
    # Save to file
    with open(file_path, 'w') as f:
        json.dump(content_data, f, indent=2)
    
    logger.info(f"Content saved to {file_path}")
    return file_path


def retrieve_content(file_id: str) -> Dict[str, Any]:
    """Retrieve content from the store based on file_id."""
    ensure_store_exists()
    
    # First try exact match with JSON format
    file_path = os.path.join(CONTENT_STORE_PATH, f"{file_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text
            with open(file_path, 'r') as f:
                content = f.read()
                return {"content": content, "metadata": {}}
    
    # If exact match fails, try normalized version with JSON extension
    safe_id = "".join(c if c.isalnum() else "_" for c in file_id)
    file_path = os.path.join(CONTENT_STORE_PATH, f"{safe_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text
            with open(file_path, 'r') as f:
                content = f.read()
                return {"content": content, "metadata": {}}
    
    # Try with other common extensions (.py, .ts, .js, .cpp, .java, .md, .txt, etc.)
    for ext in ['.py', '.ts', '.js', '.cpp', '.java', '.md', '.txt', '.html', '.css', '']:
        file_path = os.path.join(CONTENT_STORE_PATH, f"{file_id}{ext}")
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                # Infer some metadata from the file extension
                metadata = {}
                if ext == '.py':
                    metadata = {"generator_type": "code", "code_language": "py"}
                elif ext in ['.ts', '.js']:
                    metadata = {"generator_type": "code", "code_language": ext[1:]}
                elif ext == '.cpp':
                    metadata = {"generator_type": "code", "code_language": "cpp"}
                elif ext == '.java':
                    metadata = {"generator_type": "code", "code_language": "java"}
                elif ext == '.md':
                    metadata = {"generator_type": "document", "document_format": "md"}
                elif ext == '.txt':
                    metadata = {"generator_type": "document", "document_format": "txt"}
                return {"content": content, "metadata": metadata}
    
    # Look for files containing the file_id in their name
    if os.path.exists(CONTENT_STORE_PATH):
        for filename in os.listdir(CONTENT_STORE_PATH):
            if file_id.lower() in filename.lower():
                file_path = os.path.join(CONTENT_STORE_PATH, filename)
                try:
                    # If it's a JSON file, try to parse it
                    if filename.endswith('.json'):
                        with open(file_path, 'r') as f:
                            try:
                                return json.load(f)
                            except json.JSONDecodeError:
                                content = f.read()
                                return {"content": content, "metadata": {}}
                    # Otherwise, just read the content
                    else:
                        with open(file_path, 'r') as f:
                            content = f.read()
                            # Infer metadata from file extension if possible
                            ext = os.path.splitext(filename)[1]
                            metadata = {}
                            if ext == '.py':
                                metadata = {"generator_type": "code", "code_language": "py"}
                            elif ext in ['.ts', '.js']:
                                metadata = {"generator_type": "code", "code_language": ext[1:]}
                            elif ext == '.cpp':
                                metadata = {"generator_type": "code", "code_language": "cpp"}
                            elif ext == '.java':
                                metadata = {"generator_type": "code", "code_language": "java"}
                            elif ext == '.md':
                                metadata = {"generator_type": "document", "document_format": "md"}
                            elif ext == '.txt':
                                metadata = {"generator_type": "document", "document_format": "txt"}
                            return {"content": content, "metadata": metadata}
                except Exception as e:
                    logger.error(f"Error reading file {filename}: {str(e)}")
                    continue
            
    # If still not found, try fuzzy search by listing files and finding best match
    best_match = None
    best_score = 0
    
    if os.path.exists(CONTENT_STORE_PATH):
        for filename in os.listdir(CONTENT_STORE_PATH):
            # Simple string similarity - can be improved with proper fuzzy matching
            base_name = os.path.splitext(filename)[0]
            
            # Calculate similarity (very simple implementation)
            shorter = min(len(base_name), len(file_id))
            similarity = sum(1 for a, b in zip(base_name.lower(), file_id.lower()) if a == b) / max(len(base_name), len(file_id))
            
            if similarity > best_score:
                best_score = similarity
                best_match = filename
        
        if best_match and best_score > 0.5:  # Threshold for acceptable match
            file_path = os.path.join(CONTENT_STORE_PATH, best_match)
            try:
                # If it's a JSON file, try to parse it
                if best_match.endswith('.json'):
                    with open(file_path, 'r') as f:
                        try:
                            return json.load(f)
                        except json.JSONDecodeError:
                            content = f.read()
                            return {"content": content, "metadata": {}}
                # Otherwise, just read the content
                else:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        # Infer metadata from file extension if possible
                        ext = os.path.splitext(best_match)[1]
                        metadata = {}
                        if ext == '.py':
                            metadata = {"generator_type": "code", "code_language": "py"}
                        elif ext in ['.ts', '.js']:
                            metadata = {"generator_type": "code", "code_language": ext[1:]}
                        elif ext == '.cpp':
                            metadata = {"generator_type": "code", "code_language": "cpp"}
                        elif ext == '.java':
                            metadata = {"generator_type": "code", "code_language": "java"}
                        elif ext == '.md':
                            metadata = {"generator_type": "document", "document_format": "md"}
                        elif ext == '.txt':
                            metadata = {"generator_type": "document", "document_format": "txt"}
                        return {"content": content, "metadata": metadata}
            except Exception as e:
                logger.error(f"Error reading file {best_match}: {str(e)}")
    
    logger.warning(f"No content found for file_id: {file_id}")
    return {"content": "", "metadata": {}}


def content_retriever(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve previous content for update queries."""
    logger.info("Running content retriever for update queries...\n")
    
    if not isinstance(state["query"], ComplexQuery) or state["query"].action != QueryAction.UPDATE:
        logger.info("Not an update query, skipping content retrieval")
        return state
    
    file_id = state["query"].file_identifier
    if not file_id:
        logger.warning("No file identifier provided for update query")
        return state
    
    try:
        # Retrieve content based on file identifier
        content_data = retrieve_content(file_id)
        
        if content_data and content_data.get("content"):
            logger.info(f"Retrieved previous content for {file_id}")
            
            # Update state with previous content
            state["query"].previous_content = content_data.get("content", "")
            
            # Also store metadata if available
            if content_data.get("metadata"):
                # Store metadata in context for use by generators
                state["context"]["previous_content_metadata"] = content_data.get("metadata", {})
                
                # If metadata contains generator type info, use it
                if "generator_type" in content_data["metadata"]:
                    from app.core.types import GeneratorType
                    state["query"].generator_type = GeneratorType(content_data["metadata"]["generator_type"])
                
                # If metadata contains language/format info, use it
                if "code_language" in content_data["metadata"] and state["query"].generator_type == "code":
                    from app.core.types import CodeLanguage
                    state["query"].code_language = CodeLanguage(content_data["metadata"]["code_language"])
                
                if "document_format" in content_data["metadata"] and state["query"].generator_type == "document":
                    from app.core.types import DocumentFormat
                    state["query"].document_format = DocumentFormat(content_data["metadata"]["document_format"])
        else:
            logger.warning(f"No content found for {file_id}")
            # If no content is found for an update query, convert it to a new query
            # This ensures the workflow continues as a new content generation
            logger.info(f"Converting update query to new query for {file_id}")
            state["query"].action = QueryAction.NEW
            # Initialize empty context for previous content to prevent errors
            if "context" not in state:
                state["context"] = {}
            state["context"]["previous_content_metadata"] = {}
            state["query"].previous_content = ""
    except Exception as e:
        logger.error(f"Error retrieving content: {str(e)}")
        # Ensure the query can still proceed as a new query on error
        state["query"].action = QueryAction.NEW
        if "context" not in state:
            state["context"] = {}
        state["context"]["previous_content_metadata"] = {}
        state["query"].previous_content = ""
    
    return state
