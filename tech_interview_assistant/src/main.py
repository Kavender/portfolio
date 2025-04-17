import logging
import argparse
import pandas as pd
from dotenv import load_dotenv

from typing import Dict, Any, List, Optional, Union
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from langgraph.graph import END, StateGraph, START

from src.email_processor.email_processor import EmailProcessor
from src.graph.workflow_manager import WorkflowManager
from src.solution_generator.solution_generator import SolutionGenerator
from src.vector_store.vector_store_manager import VectorStoreManager
from src.vector_store.document_processor import DocumentProcessor
from src.web_scraper.web_scraper import WebScraper
from src.data_manager.data_manager import DataManager
from src.graph.retrieval import HybridRetriever
from src.utils.constants import QUESTION_PAGE_BUTTON_TEXTS
from src.utils.gmail_utils import init_google_credentials
from ipdb import set_trace


class TechInterviewAssistant:
    """
    Main class for the Tech Interview Assistant application.
    Connects EmailProcessor, SolutionGenerator with reflection, and VectorStore.
    """
    
    def __init__(
        self,
        credentials_path: str = "./src/config/gmail_api_credentials.json",
        vector_store_dir: str = "./src/data/chroma_db",
        relevancy_threshold: float = 0.7,
        max_results: int = 3,
        sender_lists: List[str] = ["interviewquery.com"]
    ):
        """
        Initialize the Tech Interview Assistant.
        
        Args:
            credentials_path: Path to Gmail API credentials
            vector_store_dir: Directory for vector store
            relevancy_threshold: Threshold for relevancy filtering
            max_results: Maximum number of results to return
        """
        # Load credentials
        self.credentials_path = credentials_path
        self.credentials = self._load_credentials()
        self.sender_lists = sender_lists
        
        # Initialize LLM and embeddings
        self.llm = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0)
        self.embeddings = OpenAIEmbeddings()
        
        # Initialize components
        self.email_processor = EmailProcessor(self.credentials)
        self.workflow_manager = WorkflowManager()
        self.solution_generator = SolutionGenerator(
            workflow_manager=self.workflow_manager,
            llm=self.llm,
            use_reflection=True,
            max_reflection_passes=3
        )
        self.vector_store_manager = VectorStoreManager(
            embedding_model=self.embeddings,
            persist_directory=vector_store_dir
        )
        self.document_processor = DocumentProcessor(solver=self.solution_generator.solver)
        self.data_manager = DataManager()
        
        # Configuration
        self.relevancy_threshold = relevancy_threshold
        self.max_results = max_results
        
        # Create the workflow graph
        self.graph = self._create_workflow_graph()
    
    def _load_credentials(self) -> Dict[str, Any]:
        """
        Load Gmail API credentials.
        
        Returns:
            Loaded credentials
        """
        return init_google_credentials()
    
    def _create_workflow_graph(self) -> StateGraph:
        """
        Create the workflow graph.
        
        Returns:
            Configured StateGraph
        """
        # Create a new StateGraph
        workflow = StateGraph(state_schema=dict)
        
        # Add nodes
        workflow.add_node("extract_questions", self._extract_questions_node)
        workflow.add_node("generate_solution", self._generate_solution_node)
        workflow.add_node("reflect_and_improve", self._reflect_and_improve_node)
        workflow.add_node("store_solution", self._store_solution_node)
        workflow.add_node("retrieve_similar", self._retrieve_similar_node)
        
        # Add edges
        workflow.add_edge(START, "extract_questions")
        workflow.add_edge("extract_questions", "generate_solution")
        workflow.add_edge("generate_solution", "reflect_and_improve")
        workflow.add_edge("reflect_and_improve", "store_solution")
        workflow.add_edge("store_solution", "retrieve_similar")
        workflow.add_edge("retrieve_similar", END)
        
        # Compile the graph without a custom checkpointer for compatibility with langraph studio
        return workflow.compile()
    
    def _extract_questions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract questions from emails.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with extracted questions
        """
        # Get sender lists from state or use default
        sender_lists = state.get("sender_lists", self.sender_lists)
        limit = state.get("email_limit", 10)
        
        # Extract questions from emails
        questions_df = self.email_processor.collect_questions_from_emails(
            sender_lists=sender_lists,
            limit=limit
        )
        
        # Update state with extracted questions
        state["questions_df"] = questions_df
        state["current_question_index"] = 0
        state["total_questions"] = len(questions_df)
        
        # Set up the first question for processing
        if len(questions_df) > 0:
            question_content = questions_df.iloc[0]["question_content"]
            question_link = questions_df.iloc[0]["link"]
            
            state["current_question"] = question_content
            state["current_link"] = question_link
            state["messages"] = [HumanMessage(content=question_content)]
        
        return state
    
    def _generate_solution_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a solution for the current question.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated solution
        """
        # Get the current question
        question = state["current_question"]
        
        # Check if we have similar examples to use
        examples = state.get("similar_examples")
        
        # Generate solution
        solution = self.solution_generator.generate_solution(
            question=question,
            examples=examples
        )
        
        # Update state with the solution
        state["candidate"] = solution["candidate"]
        
        return state
    
    def _reflect_and_improve_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reflect on and improve the generated solution.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with improved solution
        """
        # Get the current question and solution
        question = state["current_question"]
        solution = state["candidate"]
        
        # Create a reflector if not already in the solution generator
        reflector = self.solution_generator.reflector
        
        # Extract solution text
        if isinstance(solution, dict):
            if "codebase" in solution:
                codebase = solution["codebase"]
                solution_text = (
                    f"Reasoning: {codebase.get('reasoning', '')}\n\n"
                    f"Pseudocode: {codebase.get('pseudocode', '')}\n\n"
                    f"Code:\n{codebase.get('code', '')}\n\n"
                )
                if "tests" in codebase and codebase["tests"]:
                    solution_text += f"Tests:\n{codebase['tests']}\n\n"
            else:
                solution_text = str(solution)
        else:
            solution_text = str(solution)
        
        # Reflect and improve
        improved_text = reflector.reflect_and_improve(
            question=question,
            solution=solution_text,
            max_reflection_passes=3
        )
        
        # Detect and fix errors
        final_solution = reflector.detect_and_fix_errors(
            question=question,
            solution=improved_text
        )
        
        # Update state with improved solution
        state["final_solution"] = final_solution
        
        return state
    
    def _store_solution_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store the final solution in the vector store.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state after storing the solution
        """
        # Get the current question, link, and final solution
        question = state["current_question"]
        link = state["current_link"]
        solution = state["final_solution"]
        
        # Create a document
        metadata = {"source": link}
        document = self.document_processor.create_document_from_qa(
            question=question,
            solution=solution,
            metadata=metadata
        )
        
        # Add to vector store
        self.vector_store_manager.add_documents([document])
        
        # Update state
        state["stored_document"] = document
        
        return state
    
    def _retrieve_similar_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve similar questions and solutions.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with similar questions
        """
        # Get the current question
        question = state["current_question"]
        
        # Search for similar questions
        similar_docs = self.vector_store_manager.search_mmr(
            query=question,
            k=self.max_results,
            fetch_k=self.max_results * 2,
            lambda_mult=0.7  # Diversity parameter
        )
        
        # Filter by relevancy if needed
        # In a real implementation, you might compute similarity scores and filter
        
        # Update state with similar questions
        state["similar_questions"] = similar_docs
        
        return state
    
    def process_email_questions(self, sender_lists: List[str], limit: int = 10) -> Dict[str, Any]:
        """
        Process questions from emails.
        
        Args:
            sender_lists: List of sender email addresses
            limit: Maximum number of emails to process
            
        Returns:
            Results of the workflow
        """
        # Create initial state
        initial_state = {
            "sender_lists": sender_lists,
            "email_limit": limit
        }
        
        # Run the workflow
        result = self.graph.invoke(initial_state)
        
        return result
    
    def retrieve_similar_questions(self, query: str, k: int = 3) -> List[Document]:
        """
        Retrieve similar questions from the vector store.
        
        Args:
            query: Query string
            k: Number of results to return
            
        Returns:
            List of similar documents
        """
        return self.vector_store_manager.search_mmr(
            query=query,
            k=k,
            fetch_k=k * 2,
            lambda_mult=0.7
        )
    
    def setup_hybrid_retriever(self, documents: List[Document], alpha: float = 0.5, k: int = 3) -> HybridRetriever:
        """
        Set up a hybrid retriever.
        
        Args:
            documents: List of documents for the BM25 retriever
            alpha: Weight for semantic search
            k: Number of results to return
            
        Returns:
            Configured HybridRetriever
        """
        return self.vector_store_manager.setup_hybrid_retriever(
            documents=documents,
            alpha=alpha,
            k=k
        )
    
    def collect_questions_from_emails(self, sender_lists: List[str], limit: int = 1000, save_to_file: Optional[str] = None) -> pd.DataFrame:
        """
        Collect questions from emails and optionally save to a file.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            
        Returns:
            DataFrame containing links and question content
        """
        # Collect questions from emails
        email_questions = self.email_processor.collect_questions_from_emails(
            sender_lists=sender_lists,
            limit=limit
        )
        
        # Save to file if specified
        if save_to_file:
            self.data_manager.save_to_csv(email_questions, save_to_file)
        
        return email_questions
    
    def scrape_questions(self, urls: List[str], batch_size: int = 5, save_to_file: Optional[str] = None) -> pd.DataFrame:
        """
        Scrape questions and solutions from provided URLs.
        
        Args:
            urls: List of URLs to scrape
            batch_size: Number of URLs to process in each batch
            save_to_file: Optional file path to save the results
            
        Returns:
            DataFrame containing scraped questions and solutions
        """
        # Initialize web scraper
        login_page_url = "https://www.interviewquery.com/login"
        login_page_button = "div.button_inner__6ximl.button_center__HXCC_"
        web_scraper = WebScraper(login_page_url, login_page_button)
        
        try:
            # Extract questions and solutions in batches
            qa_extracted = web_scraper.extract_qa_batch(
                urls, 
                QUESTION_PAGE_BUTTON_TEXTS, 
                batch_size=batch_size
            )
            
            # Convert to DataFrame
            columns = ["id_question", "url", "question_abbr", "question_content", "solution_content"]
            df_qa_extracted = pd.DataFrame(qa_extracted, columns=columns)
            
            # Save to file if specified
            if save_to_file:
                self.data_manager.save_to_csv(df_qa_extracted, save_to_file)
            
            return df_qa_extracted
        finally:
            # Clean up
            web_scraper.close()
    
    def store_questions_from_csv(self, file_path: str, batch_size: int = 10, generate_missing: bool = True) -> int:
        """
        Store questions from a CSV file in the vector database.
        
        Args:
            file_path: Path to the CSV file containing questions
            batch_size: Number of questions to process in each batch
            generate_missing: Whether to generate solutions for missing entries
            
        Returns:
            Number of documents added to the vector store
        """
        # Load questions from CSV
        df_questions = self.data_manager.load_from_csv(file_path)
        
        # Process documents
        documents = self.document_processor.process_dataframe(
            df_questions,
            question_col='question_content',
            solution_col='solution_content',
            link_col='url',
            id_col='id_question',
            batch_size=batch_size,
            generate_missing=generate_missing
        )
        
        # Add documents to vector store
        self.vector_store_manager.add_documents(documents)
        
        return len(documents)
    
    def process_questions_batch(self, questions: Union[List[str], pd.DataFrame], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process a batch of questions.
        
        Args:
            questions: List of questions or DataFrame containing questions
            batch_size: Number of questions to process in each batch
            
        Returns:
            List of results for each question
        """
        results = []
        
        # Convert list to DataFrame if needed
        if isinstance(questions, list):
            questions_df = pd.DataFrame({"question_content": questions})
        else:
            questions_df = questions
        
        # Process in batches
        for i in range(0, len(questions_df), batch_size):
            batch = questions_df.iloc[i:i+batch_size]
            
            for _, row in batch.iterrows():
                # Get question content
                question_content = row["question_content"]
                
                # Create state with the question
                state = {
                    "current_question": question_content,
                    "current_link": row.get("link", ""),
                    "messages": [HumanMessage(content=question_content)]
                }
                
                # Run the workflow
                result = self.graph.invoke(state)
                results.append(result)
        
        return results
    
    def run_full_workflow(self, email_collection: bool = True, web_scraping: bool = False, vector_storage: bool = True) -> Dict[str, Any]:
        """
        Run the full workflow from email collection to vector storage.
        
        Args:
            email_collection: Whether to collect questions from emails
            web_scraping: Whether to scrape questions from web pages
            vector_storage: Whether to store questions in the vector database
            
        Returns:
            Dictionary with workflow results
        """
        results = {}
        
        # File paths
        fname_question_store = "./src/data/question_store.csv"
        fname_gmail_question_links = "./src/data/gmail_question_links.csv"
        
        # Step 1: Collect questions from emails
        if email_collection:
            email_questions = self.collect_questions_from_emails(
                sender_lists=self.sender_lists,
                limit=1000,
                save_to_file=fname_gmail_question_links
            )
            results["email_questions"] = len(email_questions)
        else:
            # Load from file
            email_questions = self.data_manager.load_from_csv(fname_gmail_question_links)
            results["email_questions"] = len(email_questions)
        
        # Step 2: Scrape questions and solutions
        if web_scraping:
            links = email_questions['link'].tolist()
            df_qa_extracted = self.scrape_questions(
                urls=links,
                batch_size=5,
                save_to_file=fname_question_store
            )
            results["scraped_questions"] = len(df_qa_extracted)
        else:
            # Load from file
            df_qa_extracted = self.data_manager.load_from_csv(fname_question_store)
            results["scraped_questions"] = len(df_qa_extracted)
        
        # Step 3: Store in vector database
        if vector_storage:
            documents = self.document_processor.process_dataframe(
                df_qa_extracted,
                question_col='question_content',
                solution_col='solution_content',
                link_col='url',
                id_col='id_question',
                batch_size=10,
                generate_missing=True
            )
            
            # Add documents to vector store
            self.vector_store_manager.add_documents(documents)
            results["stored_documents"] = len(documents)
            
            # Set up hybrid retriever
            hybrid_retriever = self.vector_store_manager.setup_hybrid_retriever(documents)
            results["hybrid_retriever"] = "Set up successfully"
        
        return results


def main():
    """
    Main entry point for the Tech Interview Assistant application.
    This function replaces the CLI functionality with a simpler entry point.
    """    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Tech Interview Assistant")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Process emails command
    process_parser = subparsers.add_parser("process", help="Process questions from emails")
    process_parser.add_argument(
        "--senders", 
        nargs="+", 
        default=["interviewquery.com"],
        help="List of sender email addresses to filter by"
    )
    process_parser.add_argument(
        "--limit", 
        type=int, 
        default=5,
        help="Maximum number of emails to process"
    )
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Query for similar questions")
    query_parser.add_argument(
        "query_text", 
        help="Query text to search for similar questions"
    )
    query_parser.add_argument(
        "--k", 
        type=int, 
        default=3,
        help="Number of results to return"
    )
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape questions from URLs")
    scrape_parser.add_argument(
        "urls",
        nargs="+",
        help="URLs to scrape"
    )
    scrape_parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of URLs to process in each batch"
    )
    
    # Store command
    store_parser = subparsers.add_parser("store", help="Store questions in vector database")
    store_parser.add_argument(
        "questions_file",
        help="Path to the CSV file containing questions"
    )
    store_parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of questions to process in each batch"
    )
    
    args = parser.parse_args()
    
    # Initialize the assistant
    logger.info("Initializing Tech Interview Assistant...")
    assistant = TechInterviewAssistant(
        credentials_path="./src/config/gmail_api_credentials.json",
        vector_store_dir="./src/data/chroma_db",
        relevancy_threshold=0.7,
        max_results=3
    )
    
    if args.command == "process":
        # Process questions from emails
        logger.info(f"Processing questions from emails (limit: {args.limit})...")
        result = assistant.process_email_questions(
            sender_lists=args.senders,
            limit=args.limit
        )
        
        # Print results
        logger.info(f"Processed {result.get('total_questions', 0)} questions")
        
        # Retrieve and display similar questions for the current question
        if "current_question" in result and "similar_questions" in result:
            similar_questions = result["similar_questions"]
            logger.info(f"Found {len(similar_questions)} similar questions")
            
            for i, doc in enumerate(similar_questions, 1):
                logger.info(f"Similar Question {i}:")
                logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
                logger.info(f"Content: {doc.page_content[:200]}...")  # Show first 200 chars
                logger.info("-" * 50)
    
    elif args.command == "query":
        # Retrieve similar questions
        logger.info(f"Searching for questions similar to: {args.query_text[:100]}...")
        similar_docs = assistant.retrieve_similar_questions(args.query_text, k=args.k)
        
        # Print results
        logger.info(f"Found {len(similar_docs)} similar questions")
        
        for i, doc in enumerate(similar_docs, 1):
            logger.info(f"Similar Question {i}:")
            logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
            logger.info(f"Content: {doc.page_content[:200]}...")  # Show first 200 chars
            logger.info("-" * 50)
    
    elif args.command == "scrape":
        # Scrape questions
        logger.info(f"Scraping questions from {len(args.urls)} URLs (batch size: {args.batch_size})...")
        result = assistant.scrape_questions(args.urls, batch_size=args.batch_size)
        
        # Print results
        logger.info(f"Scraped {len(result)} questions")
    
    elif args.command == "store":
        # Store questions
        logger.info(f"Storing questions from {args.questions_file} in vector database...")
        result = assistant.store_questions_from_csv(
            args.questions_file,
            batch_size=args.batch_size
        )
        
        # Print results
        logger.info(f"Stored {result} questions in vector database")
    
    else:
        parser.print_help()


# Example usage
if __name__ == "__main__":
    main()
