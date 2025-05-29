#!/usr/bin/env python
"""
Incremental Update Script for Tech Interview Assistant.

This script performs incremental updates by:
1. Checking the last run timestamp
2. Fetching new emails since that timestamp
3. Processing questions from those emails
4. Generating solutions for new questions
5. Storing everything in the vector database
6. Updating the job tracker with the new timestamp
"""
from typing import Dict, Any, List
import os
import sys
import time
import argparse
import traceback
from src.utils.logger import setup_logger
from src.services.email_service import EmailService
from src.services.question_processing_service import QuestionProcessingService
from src.services.vector_store_service import VectorStoreService
from src.services.data_service import DataService
from src.services.job_tracking_service import JobTrackingService
from src.vector_store.document_processor import DocumentProcessor

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run incremental updates for Tech Interview Assistant")
    
    parser.add_argument(
        "--sender-lists",
        nargs="+",
        default=["interviewquery.com"],
        help="List of sender email addresses to filter by"
    )
    
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode with predefined questions"
    )
    
    parser.add_argument(
        "--default-days",
        type=int,
        default=1,
        help="Default number of days to look back if no previous run is found"
    )
    
    # Check if DEFAULT_MINUTES is set in the environment (from main.py)
    default_minutes_env = os.environ.get("DEFAULT_MINUTES")
    if default_minutes_env:
        try:
            default_minutes = int(default_minutes_env)
            # Convert back to days for the argument default
            default_days = max(1, default_minutes // (24 * 60))
            parser.set_defaults(default_days=default_days)
            print(f"Using default days from environment: {default_days} (from {default_minutes} minutes)")
        except (ValueError, TypeError):
            print(f"Invalid DEFAULT_MINUTES value in environment: {default_minutes_env}, using default")
    
    parser.add_argument(
        "--email-limit",
        type=int,
        default=100,
        help="Maximum number of emails to process"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Batch size for processing questions"
    )
    
    parser.add_argument(
        "--skip-email-collection",
        action="store_true",
        help="Skip email collection step"
    )
    
    parser.add_argument(
        "--skip-solution-generation",
        action="store_true",
        help="Skip solution generation step"
    )
    
    parser.add_argument(
        "--skip-vector-storage",
        action="store_true",
        help="Skip vector storage step"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--force-collection",
        action="store_true",
        help="Force email collection regardless of last run timestamp"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Timeout in seconds for API requests (default: 900)"
    )
    
    return parser.parse_args()


# Circuit breaker state
class CircuitBreaker:
    def __init__(self, failure_threshold=3, reset_timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            
    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
        
    def can_execute(self):
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            # Check if enough time has passed to try again
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        elif self.state == "HALF_OPEN":
            return True
        return False

# Create a global circuit breaker
email_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=300)

def collect_new_emails(
    email_service: EmailService,
    job_tracking_service: JobTrackingService,
    sender_lists: List[str],
    default_days: int,
    email_limit: int,
    logger,
    force_collection: bool = False,
    timeout: int = 900  # Increased from 600 to 900
) -> Dict[str, Any]:
    """
    Collect new emails since the last run.
    
    Args:
        email_service: EmailService instance
        job_tracking_service: JobTrackingService instance
        sender_lists: List of sender email addresses to filter by
        default_days: Default number of days to look back if no previous run is found
        email_limit: Maximum number of emails to process
        logger: Logger instance
        force_collection: Whether to force collection regardless of last run timestamp
        timeout: Timeout in seconds for API requests (default: 900)
        
    Returns:
        Dictionary with results
    """
    # Check circuit breaker
    if not email_circuit_breaker.can_execute():
        logger.warning("Circuit breaker is OPEN. Skipping email collection due to previous failures.")
        return {
            "status": "skipped",
            "error": "Circuit breaker is open due to previous failures"
        }
    
    # Convert days to minutes for the email service
    default_minutes = default_days * 24 * 60
    logger.info(f"Collecting questions since last run (default: {default_days} days / {default_minutes} minutes)")
    
    # Get the last successful run
    last_run = None
    if not force_collection:
        last_run = job_tracking_service.job_tracker.get_last_successful_run("email_collection")
    
    if last_run and not force_collection:
        logger.info(f"Last successful run found: {last_run.get('end_time', 'unknown time')}")
    else:
        if force_collection:
            logger.info(f"Force collection enabled, ignoring last run timestamp and looking back {default_minutes} minutes")
        else:
            logger.ingo(f"No previous run found, will look back {default_minutes} minutes")
    
    try:
        # Collect questions from emails
        logger.info(f"Calling email_service.collect_questions_since_last_run with sender_lists={sender_lists}, default_minutes={default_minutes}, limit={email_limit}, force_collection={force_collection}, timeout={timeout}")
        logger.info(f"Using timeout of {timeout} seconds for API requests")
        
        # Set a global timeout for the entire operation
        start_time = time.time()
        
        email_questions = email_service.collect_questions_since_last_run(
            sender_lists=sender_lists,
            default_minutes=default_minutes,
            limit=email_limit,
            save_to_file="./src/data/gmail_question_links.csv",
            force_collection=force_collection,
            timeout=timeout
        )
        
        # Record success in circuit breaker
        email_circuit_breaker.record_success()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Collected {len(email_questions)} questions from emails in {elapsed_time:.2f} seconds")
        
        if len(email_questions) > 0:
            print("Example of collected questions:")
            for i, row in email_questions.head(3).iterrows():
                print(f"  Question {i+1}: {row.get('link', 'No link')} - {row.get('question_content', 'No content')[:100]}...")
    except Exception as e:
        # Record failure in circuit breaker
        email_circuit_breaker.record_failure()
        logger.error(f"Error collecting emails: {str(e)}", exc_info=True)
        traceback.print_exc()
        
        # Check for specific error types and provide more helpful messages
        error_msg = str(e).lower()
        if "timeout" in error_msg or "timed out" in error_msg:
            logger.error(f"Request timed out. Consider increasing the timeout value (current: {timeout}s)")
        elif "connection" in error_msg or "network" in error_msg:
            logger.error("Network connection issue. Check your internet connection.")
        elif "credential" in error_msg or "token" in error_msg or "auth" in error_msg:
            logger.error("Authentication issue. Check your Google API credentials.")
        
        return {
            "status": "failed",
            "error": str(e)
        }
    
    return {
        "status": "completed",
        "result": email_questions
    }


def process_questions(
    question_processing_service: QuestionProcessingService,
    email_questions,
    batch_size: int,
    logger
) -> Dict[str, Any]:
    """
    Process questions from emails.
    
    Args:
        question_processing_service: QuestionProcessingService instance
        email_questions: DataFrame of email questions
        batch_size: Batch size for processing questions
        logger: Logger instance
        
    Returns:
        Dictionary with results
    """
    logger.info(f"Processing {len(email_questions)} questions (batch size: {batch_size})")
    
    # Process questions in batches
    results = question_processing_service.process_questions_batch(
        questions=email_questions,
        batch_size=batch_size
    )
    
    logger.info(f"Processed {len(results)} questions")
    
    return {
        "status": "completed",
        "result": results
    }


def store_in_vector_db(
    vector_store_service: VectorStoreService,
    processed_questions,
    logger,
    skip_solution_generation: bool = False
) -> Dict[str, Any]:
    """
    Store processed questions in the vector database.
    
    Args:
        vector_store_service: VectorStoreService instance
        processed_questions: Processed questions
        logger: Logger instance
        skip_solution_generation: Whether solution generation was skipped
        
    Returns:
        Dictionary with results
    """
    logger.info(f"Storing {len(processed_questions)} questions in vector database")
    
    if skip_solution_generation:
        # If solution generation was skipped, we need to create dummy solutions
        # for the questions before storing them in the vector database
        from src.vector_store.document_processor import DocumentProcessor
        
        # Create a document processor
        doc_processor = DocumentProcessor(solver=None)
        
        # Create documents from the questions
        documents = []
        for _, row in processed_questions.iterrows():
            question = row.get("question_content", "")
            link = row.get("link", "")
            
            # Create a dummy solution
            dummy_solution = """
            {
            "codebase": {
                "reasoning": "This is a placeholder for a solution that will be generated later.",
                "pseudocode": "Not applicable for this question.",
                "code": "# This is a placeholder for code that will be generated later.",
                "tests": "# No tests available yet."
            },
            "report": {
                "data_preprocessing": "",
                "model_or_algorithm": "This is a placeholder for a solution that will be generated later.",
                "hyperparameters": "",
                "evaluation_metrics": "",
                "assumptions_or_caveats": "This solution has not been generated yet."
            }
            }
            """
            
            # Create a document
            document = doc_processor.create_document_from_qa(
                question=question,
                solution=dummy_solution,
                metadata={"source": link}
            )
            
            documents.append(document)
        
        # Add documents to vector store
        if documents:
            vector_store_service.add_documents(documents)
            
            result = {
                "status": "completed",
                "result": documents
            }
        else:
            result = {
                "status": "completed",
                "result": []
            }
    else:
        # Store processed questions in vector database
        result = vector_store_service.store_processed_questions(processed_questions)
    
    if result["status"] == "completed":
        logger.info(f"Stored {len(result.get('result', []))} documents in vector database")
    else:
        logger.error(f"Error storing in vector database: {result.get('error', 'Unknown error')}")
    
    return result


def main():
    """
    Main entry point for the script.
    """
    args = parse_args()
    print(f"Starting incremental update with args: {args}")
    
    # Set up logging
    logger = setup_logger(
        name="incremental_update",
        console_output=True,
        file_output=True,
        structured_logging=False
    )
    logger.info("Logger initialized")
    
    # Initialize services
    job_tracking_service = JobTrackingService()
    email_service = EmailService(job_tracker=job_tracking_service.job_tracker)
    question_processing_service = QuestionProcessingService(job_tracker=job_tracking_service.job_tracker)
    
    # Initialize document processor for vector store service
    document_processor = DocumentProcessor(solver=question_processing_service.solution_generator.solver)
    vector_store_service = VectorStoreService(
        job_tracker=job_tracking_service.job_tracker,
        document_processor=document_processor
    )
    
    # Initialize data service
    data_service = DataService(job_tracker=job_tracking_service.job_tracker)
    logger.info("Starting incremental update")
    
    # Step 1: Collect new emails
    if not args.skip_email_collection:
        logger.info("Collecting new emails")
        email_result = collect_new_emails(
            email_service=email_service,
            job_tracking_service=job_tracking_service,
            sender_lists=args.sender_lists,
            default_days=args.default_days,
            email_limit=args.email_limit,
            logger=logger,
            force_collection=args.force_collection,
            timeout=args.timeout
        )
        
        if email_result["status"] == "failed":
            logger.error(f"Email collection failed: {email_result.get('error', 'Unknown error')}")
            return
        
        email_questions = email_result["result"]
        
        if len(email_questions) == 0:
            logger.info("No new emails found, exiting")
            return
    else:
        # TODO: LET'S REMOVE THIS OPTION?
        logger.info("Skipping email collection")
        email_questions = data_service.load_from_csv("./src/data/gmail_question_links.csv")
    
    # Step 2: Process questions
    if not args.skip_solution_generation:
        logger.info("Processing questions")
        process_result = process_questions(
            question_processing_service=question_processing_service,
            email_questions=email_questions,
            batch_size=args.batch_size,
            logger=logger
        )
        
        if process_result["status"] == "failed":
            logger.error(f"Question processing failed: {process_result.get('error', 'Unknown error')}")
            return
        
        processed_questions = process_result["result"]
    else:
        logger.info("Skipping solution generation")
        processed_questions = email_questions
    
    # Step 3: Store in vector database
    if not args.skip_vector_storage:
        logger.info("Storing in vector database")
        store_result = store_in_vector_db(
            vector_store_service=vector_store_service,
            processed_questions=processed_questions,
            logger=logger,
            skip_solution_generation=args.skip_solution_generation
        )
        
        if store_result["status"] == "failed":
            logger.error(f"Vector storage failed: {store_result.get('error', 'Unknown error')}")
            return
    else:
        logger.info("Skipping vector storage")
    
    logger.info("Incremental update completed successfully")


if __name__ == "__main__":
    main()
