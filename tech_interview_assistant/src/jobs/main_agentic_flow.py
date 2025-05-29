from typing import Dict, Any, List, Optional, Union
import pandas as pd
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_core.documents import Document
from langgraph.graph import END, StateGraph, START

from src.utils.logger import get_logger
from src.graph.retrieval import HybridRetriever
from src.graph.workflow_manager import WorkflowManager
from src.vector_store.document_processor import DocumentProcessor
from src.email_processor.gmail_utils import init_google_credentials
from src.services.data_service import DataService
from src.services.email_service import EmailService
from src.services.question_processing_service import QuestionProcessingService
from src.services.vector_store_service import VectorStoreService
from src.services.job_tracking_service import JobTrackingService


class TechInterviewAssistant:
    """
    Main class for the Tech Interview Assistant application.
    
    This class serves as a facade that coordinates the various services
    that make up the application.
    """
    
    def __init__(
        self,
        credentials_path: str = "./src/config/gmail_api_credentials.json",
        vector_store_dir: str = "./src/data/chroma_db",
        relevancy_threshold: float = 0.7,
        max_results: int = 3,
        max_email_collected: int = 100,
        sender_lists: List[str] = ["interviewquery.com"],
        job_tracker_db_path: str = "./src/data/job_tracker.db",
        fname_question_store = "./src/data/question_store.csv",
        fname_gmail_question_links = "./src/data/gmail_question_links.csv"
    ):
        """
        Initialize the Tech Interview Assistant.
        
        Args:
            credentials_path: Path to Gmail API credentials
            vector_store_dir: Directory for vector store
            relevancy_threshold: Threshold for relevancy filtering
            max_results: Maximum number of results to return
            max_email_collected: Maximum number of email collected per run
            sender_lists: Default list of sender email addresses to filter by
            job_tracker_db_path: Path to the job tracker database
            fname_question_store: Path to question parsed from url and stored locally
            fname_gmail_question_links: Path to question collected from email
        """
        # Set up logging
        self.logger = get_logger("tech_interview_assistant")
        self.logger.info("Initializing Tech Interview Assistant")
        
        # Initialize services
        self.job_tracking_service = JobTrackingService(db_path=job_tracker_db_path)
        self.email_service = EmailService(
            credentials_path=credentials_path,
            job_tracker=self.job_tracking_service.job_tracker,
            sender_lists=sender_lists
        )
        self.question_processing_service = QuestionProcessingService(
            job_tracker=self.job_tracking_service.job_tracker
        )
        
        # Initialize document processor for vector store service
        self.document_processor = DocumentProcessor(
            solver=self.question_processing_service.solution_generator.solver
        )
        self.vector_store_service = VectorStoreService(
            vector_store_dir=vector_store_dir,
            job_tracker=self.job_tracking_service.job_tracker,
            document_processor=self.document_processor,
            relevancy_threshold=relevancy_threshold,
            max_results=max_results
        )
        
        # Initialize data service
        self.data_service = DataService(job_tracker=self.job_tracking_service.job_tracker)
        
        # Configuration
        self.sender_lists = sender_lists
        self.relevancy_threshold = relevancy_threshold
        self.max_results = max_results
        self.max_email_collected = max_email_collected
        self.fname_question_store = fname_question_store
        self.fname_gmail_question_links = fname_gmail_question_links
        
        # Initialize the WorkflowManager for question solving
        self.workflow_manager = WorkflowManager()
        
        # Create the main workflow graph for the full pipeline
        self.graph = self._create_workflow_graph()
        self.logger.info("Tech Interview Assistant initialized successfully")
    
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
        workflow = StateGraph(state_schema=dict)
        
        # Add nodes
        workflow.add_node("extract_questions", self._extract_questions_node)
        workflow.add_node("generate_solution", self._generate_solution_node)
        workflow.add_node("reflect_and_improve", self._reflect_and_improve_node)
        workflow.add_node("store_solution", self._store_solution_node)
        workflow.add_node("retrieve_similar", self._retrieve_similar_node)
        workflow.add_node("check_more_questions", self._check_more_questions_node)
        
        # Add edges
        workflow.add_edge(START, "extract_questions")
        workflow.add_edge("extract_questions", "generate_solution")
        workflow.add_edge("generate_solution", "reflect_and_improve")
        workflow.add_edge("reflect_and_improve", "store_solution")
        workflow.add_edge("store_solution", "retrieve_similar")
        workflow.add_edge("retrieve_similar", "check_more_questions")
        
        # Add conditional edge for processing more questions or ending
        workflow.add_conditional_edges(
            "check_more_questions",
            self._has_more_questions,
            {
                True: "extract_questions",  # Loop back to process next question
                False: END                  # End workflow when all questions processed
            }
        )

        # Compile the graph
        return workflow.compile()
    
    def _extract_questions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract questions from emails or set up the next question for processing.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with the current question to process
        """
        # Check if we already have questions_df in the state
        if "questions_df" not in state:
            # First run - extract questions from emails
            sender_lists = state.get("sender_lists", self.sender_lists)
            limit = state.get("email_limit", self.max_email_collected)
            
            # Extract questions from emails
            questions_df = self.email_service.collect_questions_from_emails(
                sender_lists=sender_lists,
                limit=limit
            )
            
            # Update state with extracted questions
            state["questions_df"] = questions_df
            state["current_question_index"] = 0
            state["total_questions"] = len(questions_df)
            
            self.logger.info(f"Extracted {len(questions_df)} questions from emails")
        else:
            # Subsequent runs - increment the question index
            current_index = state.get("current_question_index", 0)
            state["current_question_index"] = current_index + 1
            
            self.logger.info(f"Processing question {state['current_question_index'] + 1} of {state['total_questions']}")
        
        # Set up the current question for processing
        questions_df = state["questions_df"]
        current_index = state["current_question_index"]
        
        if len(questions_df) > current_index:
            question_content = questions_df.iloc[current_index]["question_content"]
            question_link = questions_df.iloc[current_index]["link"]
            
            state["current_question"] = question_content
            state["current_link"] = question_link
            state["messages"] = [HumanMessage(content=question_content)]
            
            self.logger.info(f"Set up question for processing: {question_content[:100]}...")
        else:
            self.logger.warning(f"No question found at index {current_index}")
        
        return state
    
    def _generate_solution_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a solution for the current question using WorkflowManager.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with generated solution
        """
        question = state["current_question"]
        
        # Use WorkflowManager to solve the question
        workflow_result = self.workflow_manager.return_graph().invoke({
            "messages": [HumanMessage(content=question)]
        })
        
        # Extract the solution from the workflow result
        if "candidate" in workflow_result:
            state["candidate"] = workflow_result["candidate"]
        else:
            # Fallback to using question_processing_service directly
            solution = self.question_processing_service.solution_generator.generate_solution(
                question=question,
                examples=state.get("similar_examples")
            )
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
        question = state["current_question"]
        solution = state["candidate"]
        reflector = self.solution_generator.reflector
        
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
        
        improved_text = reflector.reflect_and_improve(
            question=question,
            solution=solution_text,
            max_reflection_passes=3
        )
        
        final_solution = reflector.detect_and_fix_errors(
            question=question,
            solution=improved_text
        )
        
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
        question = state["current_question"]
        link = state["current_link"]
        solution = state["final_solution"]
        
        metadata = {"source": link}
        document = self.document_processor.create_document_from_qa(
            question=question,
            solution=solution,
            metadata=metadata
        )
        
        self.vector_store_service.add_documents([document])
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
        question = state["current_question"]
        similar_docs = self.retrieve_similar_questions(query=question, 
                                                       k=self.max_results)
        
        # Filter by relevancy if needed
        # In a real implementation, you might compute similarity scores and filter
        
        state["similar_questions"] = similar_docs
        
        return state
        
    def _check_more_questions_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if there are more questions to process.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with has_more_questions flag
        """
        current_index = state.get("current_question_index", 0)
        total_questions = state.get("total_questions", 0)
        
        # Check if there are more questions to process
        has_more_questions = current_index < total_questions - 1
        
        # Update state with the flag
        state["has_more_questions"] = has_more_questions
        
        if has_more_questions:
            self.logger.info(f"More questions to process: {current_index + 1}/{total_questions} completed")
        else:
            self.logger.info(f"All questions processed: {total_questions}/{total_questions} completed")
        
        return state
    
    def _has_more_questions(self, state: Dict[str, Any]) -> bool:
        """
        Conditional function to check if there are more questions to process.
        
        Args:
            state: Current workflow state
            
        Returns:
            True if there are more questions to process, False otherwise
        """
        return state.get("has_more_questions", False)
    
    def process_email_questions(self, sender_lists: List[str], limit: int = 10) -> Dict[str, Any]:
        """
        Process questions from emails.
        
        Args:
            sender_lists: List of sender email addresses
            limit: Maximum number of emails to process
            
        Returns:
            Results of the workflow
        """
        initial_state = {
            "sender_lists": sender_lists,
            "email_limit": limit
        }

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
        return self.vector_store_service.search_mmr(
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
        return self.vector_store_service.setup_hybrid_retriever(
            documents=documents,
            alpha=alpha,
            k=k
        )
    
    def collect_questions_from_emails(self, sender_lists: List[str], limit: int = 1000, save_to_file: Optional[str] = None, since_timestamp: Optional[datetime] = None) -> pd.DataFrame:
        """
        Collect questions from emails and optionally save to a file.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            since_timestamp: Optional datetime to filter emails by timestamp
            
        Returns:
            DataFrame containing links and question content
        """
        self.logger.info(f"Collecting questions from emails (limit: {limit})")
        
        # Use the email service to collect questions
        return self.email_service.collect_questions_from_emails(
            sender_lists=sender_lists,
            limit=limit,
            since_timestamp=since_timestamp,
            save_to_file=save_to_file
        )
    
    def collect_questions_since_last_run(self, sender_lists: List[str] = None, default_minutes: int = 60, limit: int = 1000, save_to_file: Optional[str] = None) -> pd.DataFrame:
        """
        Collect questions from emails received since the last successful run.
        
        Args:
            sender_lists: List of sender email addresses to filter by (defaults to self.sender_lists)
            default_minutes: Default number of minutes to look back if no successful run is found
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            
        Returns:
            DataFrame containing links and question content
        """
        if sender_lists is None:
            sender_lists = self.sender_lists
            
        self.logger.info(f"Collecting questions since last run (default: {default_minutes} minutes)")
        
        # Use the email service to collect questions since the last run
        return self.email_service.collect_questions_since_last_run(
            sender_lists=sender_lists,
            default_minutes=default_minutes,
            limit=limit,
            save_to_file=save_to_file
        )
    
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
        return self.data_service.scrape_questions(
            urls=urls,
            batch_size=batch_size,
            save_to_file=save_to_file
    )
    
    def process_questions_batch(self, questions: Union[List[str], pd.DataFrame], batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        Process a batch of questions.
        
        Args:
            questions: List of questions or DataFrame containing questions
            batch_size: Number of questions to process in each batch
            
        Returns:
            List of results for each question
        """
        self.logger.info(f"Processing batch of {len(questions) if isinstance(questions, list) else len(questions.index)} questions")
        
        # Use the question processing service to process the batch
        return self.question_processing_service.process_questions_batch(
            questions=questions,
            batch_size=batch_size
        )
    
    def run_full_workflow(self, email_collection: bool = True, web_scraping: bool = True, vector_storage: bool = True) -> Dict[str, Any]:
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
        
        # Step 1: Collect questions from emails
        if email_collection:
            email_questions = self.collect_questions_from_emails(
                sender_lists=self.sender_lists,
                limit=self.max_email_collected,
                save_to_file=self.fname_gmail_question_links
            )
            results["email_questions"] = len(email_questions)
        else:
            # Load from file
            email_questions = self.data_manager.load_from_csv(self.fname_gmail_question_links)
            results["email_questions"] = len(email_questions)
        
        # Step 2: Scrape questions and solutions
        if web_scraping:
            links = email_questions['link'].tolist()
            df_qa_extracted = self.scrape_questions(
                urls=links,
                batch_size=5,
                save_to_file=self.fname_question_store
            )
            results["scraped_questions"] = len(df_qa_extracted)
        else:
            # Load from file
            df_qa_extracted = self.data_manager.load_from_csv(self.fname_question_store)
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
            self.vector_store_manager.setup_hybrid_retriever(documents)
            results["hybrid_retriever"] = "Set up successfully"
        
        return results
