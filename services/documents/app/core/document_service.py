"""
Core document service implementation with vector store and RAG capabilities.
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.document_loaders import (
    TextLoader,
    PDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
from langchain.schema import Document

class DocumentService:
    """Document service for handling document processing, embedding, and retrieval."""
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """Initialize the document service."""
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model_name)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        
        # Initialize vector store
        self.vector_store = Chroma(
            persist_directory=str(self.persist_directory),
            embedding_function=self.embeddings,
        )
    
    def _get_loader(self, file_path: str):
        """Get appropriate loader based on file extension."""
        file_extension = Path(file_path).suffix.lower()
        loaders = {
            '.txt': TextLoader,
            '.pdf': PDFLoader,
            '.docx': Docx2txtLoader,
            '.md': UnstructuredMarkdownLoader,
        }
        loader_class = loaders.get(file_extension)
        if not loader_class:
            raise ValueError(f"Unsupported file type: {file_extension}")
        return loader_class(file_path)
    
    async def process_document(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Process a document and store it in the vector store."""
        try:
            # Load document
            loader = self._get_loader(file_path)
            documents = loader.load()
            
            # Split documents
            splits = self.text_splitter.split_documents(documents)
            
            # Add metadata if provided
            if metadata:
                for split in splits:
                    split.metadata.update(metadata)
            
            # Add to vector store
            self.vector_store.add_documents(splits)
            self.vector_store.persist()
            
            return "Document processed successfully"
        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")
    
    async def semantic_search(
        self,
        query: str,
        k: int = 4,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Perform semantic search on the vector store."""
        try:
            results = self.vector_store.similarity_search(
                query,
                k=k,
                filter=filter_criteria
            )
            return results
        except Exception as e:
            raise Exception(f"Error performing semantic search: {str(e)}")
    
    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Retrieve a specific document by ID."""
        try:
            return self.vector_store.get(doc_id)
        except Exception as e:
            raise Exception(f"Error retrieving document: {str(e)}")
    
    async def delete_document(self, doc_id: str) -> bool:
        """Delete a document from the vector store."""
        try:
            self.vector_store.delete(doc_id)
            return True
        except Exception as e:
            raise Exception(f"Error deleting document: {str(e)}") 