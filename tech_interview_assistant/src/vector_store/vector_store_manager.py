from typing import List
import os
import chromadb
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from graph.retrieval import HybridRetriever


class VectorStoreManager:
    """
    Class for managing vector stores and retrievers.
    """
    
    def __init__(self, embedding_model, persist_directory: str = "./data/chroma_db"):
        """
        Initialize the VectorStoreManager with an embedding model.
        
        Args:
            embedding_model: The embedding model to use for vectorization
            persist_directory: Directory to persist the vector store
        """
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory
        self.vector_store = self._initialize_vector_store()
    
    def _initialize_vector_store(self) -> Chroma:
        """
        Initialize the vector store.
        
        Returns:
            Initialized Chroma vector store
        """
        # Create the directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize with direct client creation to avoid deprecated configuration
        # Disable telemetry to avoid connection errors
        client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        
        # Create or get the collection
        try:
            collection = client.get_or_create_collection(name="tech_interview_qa")
        except Exception as e:
            # If there's an error, try to get the collection directly
            collection = client.get_collection(name="tech_interview_qa")
        
        # Initialize and return the vector store
        return Chroma(
            client=client,
            collection_name="tech_interview_qa",
            embedding_function=self.embedding_model
        )
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents to add
        """
        self.vector_store.add_documents(documents)
        # self.vector_store.persist()
    
    def setup_hybrid_retriever(self, documents: List[Document], alpha: float = 0.5, k: int = 3) -> HybridRetriever:
        """
        Set up a hybrid retriever combining BM25 and vector search.
        
        Args:
            documents: List of documents to use for BM25 retriever
            alpha: Weight for semantic search (0-1)
            k: Number of final results to return
            
        Returns:
            Configured HybridRetriever
        """
        # Initialize BM25 retriever
        bm25_retriever = BM25Retriever.from_documents(documents)
        bm25_retriever.k = k * 2  # Retrieve more documents for better filtering
        
        # Create and return the hybrid retriever
        return HybridRetriever(
            bm25_retriever=bm25_retriever,
            vectorstore=self.vector_store,
            embeddings=self.embedding_model,
            alpha=alpha,
            k=k
        )
    
    def search(self, query: str, k: int = 3) -> List[Document]:
        """
        Search the vector store for documents matching the query.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of matching documents
        """
        return self.vector_store.similarity_search(query, k=k)
    
    def search_mmr(self, query: str, k: int = 3, fetch_k: int = 10, lambda_mult: float = 0.5) -> List[Document]:
        """
        Search the vector store using Maximal Marginal Relevance.
        
        Args:
            query: Query string
            k: Number of results to return
            fetch_k: Number of documents to fetch before filtering
            lambda_mult: Diversity parameter (0-1)
            
        Returns:
            List of matching documents
        """
        return self.vector_store.max_marginal_relevance_search(
            query, 
            k=k, 
            fetch_k=fetch_k, 
            lambda_mult=lambda_mult
        )
    
    def get_collection_stats(self) -> dict:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with collection statistics
        """
        return {
            "collection_name": self.vector_store._collection.name,
            "count": self.vector_store._collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def get_all_documents(self) -> List[Document]:
        """
        Retrieve all documents stored in the vector store.
        
        Returns:
            List of all documents in the vector store
        """
        # Get all documents from the collection
        collection_data = self.vector_store._collection.get()
        
        # Convert to LangChain Document objects
        documents = []
        
        # Check if there are any documents in the collection
        if collection_data["ids"] and len(collection_data["ids"]) > 0:
            for i in range(len(collection_data["ids"])):
                # Extract document data
                doc_id = collection_data["ids"][i]
                metadata = collection_data["metadatas"][i] if collection_data["metadatas"] else {}
                content = collection_data["documents"][i] if collection_data["documents"] else ""
                
                # Create Document object
                doc = Document(
                    page_content=content,
                    metadata=metadata
                )
                documents.append(doc)
        
        return documents
