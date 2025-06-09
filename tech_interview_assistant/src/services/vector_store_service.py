from typing import List, Dict, Any, Optional
import time
import pandas as pd
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

from vector_store.vector_store_manager import VectorStoreManager
from vector_store.document_processor import DocumentProcessor
from graph.retrieval import HybridRetriever
from data_manager.job_tracker import JobTracker
from utils.logger import get_logger


class VectorStoreService:
    """
    Service for handling vector store operations.
    
    This service encapsulates functionality related to storing, retrieving,
    and searching documents in the vector database.
    """
    
    def __init__(
        self,
        vector_store_dir: str = "./src/data/chroma_db",
        job_tracker: Optional[JobTracker] = None,
        embedding_model: Optional[Any] = None,
        document_processor: Optional[DocumentProcessor] = None,
        relevancy_threshold: float = 0.7,
        max_results: int = 3
    ):
        """
        Initialize the VectorStoreService.
        
        Args:
            vector_store_dir: Directory for vector store
            job_tracker: JobTracker instance for tracking jobs
            embedding_model: Embedding model to use
            document_processor: DocumentProcessor instance
            relevancy_threshold: Threshold for relevancy filtering
            max_results: Maximum number of results to return
        """
        self.logger = get_logger("vector_store_service")
        self.logger.info("Initializing VectorStoreService")
        
        # Initialize embedding model if not provided
        if embedding_model is None:
            self.embeddings = OpenAIEmbeddings()
        else:
            self.embeddings = embedding_model
        
        # Initialize vector store manager
        self.vector_store_manager = VectorStoreManager(
            embedding_model=self.embeddings,
            persist_directory=vector_store_dir
        )
        
        # Initialize document processor if not provided
        self.document_processor = document_processor
        
        # Initialize job tracker if provided, otherwise create a new one
        if job_tracker:
            self.job_tracker = job_tracker
        else:
            self.job_tracker = JobTracker()
        
        # Configuration
        self.relevancy_threshold = relevancy_threshold
        self.max_results = max_results
        
        self.logger.info("VectorStoreService initialized successfully")
    
    def add_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents to add
            
        Returns:
            Dictionary with results
        """
        # Start job tracking
        job_run_id = self.job_tracker.start_job("vector_storage", {
            "num_documents": len(documents)
        })
        
        try:
            start_time = time.time()
            
            # Add documents to vector store
            self.vector_store_manager.add_documents(documents)
            
            end_time = time.time()
            
            # Record metrics
            metrics = {
                "duration_seconds": end_time - start_time,
                "documents_stored": len(documents)
            }
            
            self.job_tracker.record_metrics(job_run_id, metrics)
            self.job_tracker.end_job(job_run_id, "completed")
            
            self.logger.info(f"Stored {len(documents)} documents in vector database")
            
            return {
                "job_run_id": job_run_id,
                "status": "completed",
                "metrics": metrics,
                "result": documents
            }
            
        except Exception as e:
            self.logger.error(f"Error storing in vector database: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            return {
                "job_run_id": job_run_id,
                "status": "failed",
                "error": str(e)
            }
    
    def search(self, query: str, k: int = None) -> List[Document]:
        """
        Search for documents in the vector store.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of documents
        """
        if k is None:
            k = self.max_results
            
        return self.vector_store_manager.search(query=query, k=k)
    
    def search_mmr(self, query: str, k: int = None, fetch_k: int = None, lambda_mult: float = 0.7) -> List[Document]:
        """
        Search for documents in the vector store using MMR.
        
        Args:
            query: Query string
            k: Number of results to return
            fetch_k: Number of results to fetch before applying MMR
            lambda_mult: Diversity parameter
            
        Returns:
            List of documents
        """
        if k is None:
            k = self.max_results
            
        if fetch_k is None:
            fetch_k = k * 2
            
        return self.vector_store_manager.search_mmr(
            query=query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult
        )
    
    def setup_hybrid_retriever(self, documents: List[Document], alpha: float = 0.5, k: int = None) -> HybridRetriever:
        """
        Set up a hybrid retriever.
        
        Args:
            documents: List of documents for the BM25 retriever
            alpha: Weight for semantic search
            k: Number of results to return
            
        Returns:
            Configured HybridRetriever
        """
        if k is None:
            k = self.max_results
            
        return self.vector_store_manager.setup_hybrid_retriever(
            documents=documents,
            alpha=alpha,
            k=k
        )
    
    def store_processed_questions(
        self, 
        processed_questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store processed questions in the vector database.
        
        Args:
            processed_questions: List of processed questions
            
        Returns:
            Dictionary with results
        """
        if not self.document_processor:
            self.logger.error("Document processor not initialized")
            return {
                "status": "failed",
                "error": "Document processor not initialized"
            }
            
        # Start job tracking
        job_run_id = self.job_tracker.start_job("vector_storage", {
            "num_questions": len(processed_questions)
        })
        
        try:
            # Extract documents from processed questions
            start_time = time.time()
            
            # Convert processed questions to a format suitable for the vector store
            documents = []
            for result in processed_questions:
                if "final_solution" in result and "current_question" in result:
                    document = self.document_processor.create_document_from_qa(
                        question=result["current_question"],
                        solution=result["final_solution"],
                        metadata={"source": result.get("current_link", "")}
                    )
                    documents.append(document)
            
            # Add documents to vector store
            if documents:
                self.vector_store_manager.add_documents(documents)
            
            end_time = time.time()
            
            # Record metrics
            metrics = {
                "duration_seconds": end_time - start_time,
                "documents_stored": len(documents)
            }
            
            self.job_tracker.record_metrics(job_run_id, metrics)
            self.job_tracker.end_job(job_run_id, "completed")
            
            self.logger.info(f"Stored {len(documents)} documents in vector database")
            
            return {
                "job_run_id": job_run_id,
                "status": "completed",
                "metrics": metrics,
                "result": documents
            }
            
        except Exception as e:
            self.logger.error(f"Error storing in vector database: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            return {
                "job_run_id": job_run_id,
                "status": "failed",
                "error": str(e)
            }
    
    def get_all_documents(self) -> Dict[str, Any]:
        """
        Retrieve all documents stored in the vector store.
        
        Returns:
            Dictionary with results containing all documents
        """
        # Start job tracking
        job_run_id = self.job_tracker.start_job("vector_retrieval", {
            "operation": "get_all_documents"
        })
        
        try:
            start_time = time.time()
            
            # Retrieve all documents from vector store
            documents = self.vector_store_manager.get_all_documents()
            
            end_time = time.time()
            
            # Record metrics
            metrics = {
                "duration_seconds": end_time - start_time,
                "documents_retrieved": len(documents)
            }
            
            self.job_tracker.record_metrics(job_run_id, metrics)
            self.job_tracker.end_job(job_run_id, "completed")
            
            self.logger.info(f"Retrieved {len(documents)} documents from vector database")
            
            return {
                "job_run_id": job_run_id,
                "status": "completed",
                "metrics": metrics,
                "result": documents
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving documents from vector database: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            return {
                "job_run_id": job_run_id,
                "status": "failed",
                "error": str(e)
            }
