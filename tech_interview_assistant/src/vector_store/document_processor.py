from typing import List, Dict, Any, Optional
import logging
import pandas as pd
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from graph.retrieval import format_example
from utils.logger import default_logger as logger


# TODO: is the class really necessary, if not, let's remove the mode and only keep the solution_generator
class DocumentProcessor:
    """
    Class for processing documents for vector storage.
    """
    
    def __init__(self, solver=None):
        """
        Initialize the DocumentProcessor.
        
        Args:
            solver: Optional solver for generating solutions
        """
        self.solver = solver
    
    def generate_solution(self, question_content: str) -> Any:
        """
        Generate a solution for a question using the provided solver.
        
        Args:
            question_content: The question text
            
        Returns:
            Generated solution
        """
        if self.solver is None:
            raise ValueError("Solver not provided. Cannot generate solution.")
        
        # Create state with messages containing the question
        state = {"messages": [HumanMessage(content=question_content)]}
        
        # Use solver to generate solution
        result = self.solver(state)
        return result["candidate"]
    
    def process_dataframe(
        self, 
        df: pd.DataFrame, 
        question_col: str = 'question_content', 
        solution_col: str = 'solution_content',
        link_col: Optional[str] = 'link',
        id_col: Optional[str] = 'id_question',
        batch_size: int = 10,
        generate_missing: bool = True
    ) -> List[Document]:
        """
        Process a DataFrame of questions and solutions into documents.
        
        Args:
            df: DataFrame containing questions and solutions
            question_col: Column name for questions
            solution_col: Column name for solutions
            link_col: Column name for links (optional)
            id_col: Column name for IDs (optional)
            batch_size: Number of documents to process in each batch
            generate_missing: Whether to generate solutions for missing entries
            
        Returns:
            List of processed documents
        """
        all_documents = []
        
        # Process in batches to avoid memory issues
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            batch_documents = []
            
            for _, row in batch_df.iterrows():
                # Get question and solution
                question = row[question_col]
                solution = row.get(solution_col, '')
                
                # Generate solution if none exists and generation is enabled
                if (not solution or len(solution.strip()) == 0) and generate_missing and self.solver:
                    logger.info(f"Generating solution for question: {row.get('question_abbr', 'Unknown')}")
                    solution_obj = self.generate_solution(question)
                    solution = solution_obj.dict() if hasattr(solution_obj, 'dict') else str(solution_obj)
                
                # Skip if still no solution and generation was disabled
                if not solution or len(solution.strip()) == 0:
                    logger.warning(f"Skipping question without solution: {row.get('question_abbr', 'Unknown')}")
                    continue
                
                # Format for storage
                formatted_qa = format_example(question, solution)
                
                # Prepare metadata
                metadata = {}
                if link_col and link_col in row:
                    metadata["source"] = row[link_col]
                if id_col and id_col in row:
                    metadata["id"] = row[id_col]
                
                # Create document
                document = Document(page_content=formatted_qa, metadata=metadata)
                batch_documents.append(document)
            
            all_documents.extend(batch_documents)
            logger.info(f"Processed batch {i//batch_size + 1}, documents: {len(batch_documents)}")
        
        return all_documents
    
    def create_document_from_qa(
        self, 
        question: str, 
        solution: Any, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Create a document from a question and solution.
        
        Args:
            question: Question text
            solution: Solution object or text
            metadata: Optional metadata for the document
            
        Returns:
            Document object
        """
        formatted_qa = format_example(question, solution)
        return Document(page_content=formatted_qa, metadata=metadata or {})
