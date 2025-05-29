import os
import sys
import logging
import argparse
from dotenv import load_dotenv
from jobs.main_agentic_flow import TechInterviewAssistant
from jobs.run_incremental_update import main as run_incremental_update
from src.utils.logger import default_logger as logger


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
    
    # Incremental update command
    incremental_parser = subparsers.add_parser("incremental", help="Run incremental update to process new emails")
    incremental_parser.add_argument(
        "--senders", 
        nargs="+", 
        default=["interviewquery.com"],
        help="List of sender email addresses to filter by"
    )
    incremental_parser.add_argument(
        "--default-days", 
        type=int, 
        default=1,
        help="Default number of days to look back if no previous run is found"
    )
    incremental_parser.add_argument(
        "--limit", 
        type=int, 
        default=100,
        help="Maximum number of emails to process"
    )
    incremental_parser.add_argument(
        "--force-collection",
        action="store_true",
        help="Force email collection regardless of last run timestamp"
    )
    incremental_parser.add_argument(
        "--skip-solution-generation",
        action="store_true",
        help="Skip solution generation step"
    )
    incremental_parser.add_argument(
        "--skip-vector-storage",
        action="store_true",
        help="Skip vector storage step"
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
        logger.info(f"Found {len(similar_docs)} similar questions")
        
        for i, doc in enumerate(similar_docs, 1):
            logger.info(f"Similar Question {i}:")
            logger.info(f"Source: {doc.metadata.get('source', 'Unknown')}")
            logger.info(f"Content: {doc.page_content[:200]}...")  # Show first 200 chars
            logger.info("-" * 50)
    
    elif args.command == "scrape":
        logger.info(f"Scraping questions from {len(args.urls)} URLs (batch size: {args.batch_size})...")
        result = assistant.scrape_questions(args.urls, batch_size=args.batch_size)
        logger.info(f"Scraped {len(result)} questions")
    
    elif args.command == "incremental":
        logger.info("Running incremental update script...")
        
        # Convert days to minutes for the incremental update
        default_minutes = args.default_days * 24 * 60
        logger.info(f"Converting {args.default_days} days to {default_minutes} minutes for email lookup")
        
        # Set the default_minutes in the environment for the incremental update script
        os.environ["DEFAULT_MINUTES"] = str(default_minutes)
        
        # Pass any additional arguments to the incremental update script
        sys.argv = [
            "run_incremental_update.py",
            "--default-days", str(args.default_days),
            "--email-limit", str(args.limit)
        ]
        
        if args.force_collection:
            sys.argv.append("--force-collection")
        if args.skip_solution_generation:
            sys.argv.append("--skip-solution-generation")
        if args.skip_vector_storage:
            sys.argv.append("--skip-vector-storage")
        if args.senders:
            sys.argv.extend(["--sender-lists"] + args.senders)
        
        run_incremental_update()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
