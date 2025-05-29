from typing import List, Dict, Any, Optional
import time
import pandas as pd
from datetime import datetime, timedelta
from src.utils.logger import get_logger
from src.data_manager.job_tracker import JobTracker
from src.email_processor.email_processor import EmailProcessor
from src.email_processor.gmail_utils import init_google_credentials


class EmailService:
    """
    Service for handling email operations.
    
    This service encapsulates functionality related to collecting and processing
    emails, including incremental collection based on timestamps.
    """
    
    def __init__(
        self,
        credentials_path: str = "./src/config/gmail_api_credentials.json",
        job_tracker: Optional[JobTracker] = None,
        sender_lists: List[str] = ["interviewquery.com"]
    ):
        """
        Initialize the EmailService.
        
        Args:
            credentials_path: Path to Gmail API credentials
            job_tracker: JobTracker instance for tracking jobs
            sender_lists: Default list of sender email addresses to filter by
        """
        self.logger = get_logger("email_service")
        self.logger.info("Initializing EmailService")
        
        # Load credentials
        self.credentials_path = credentials_path
        self.credentials = self._load_credentials()
        self.sender_lists = sender_lists
        
        # Initialize components
        self.email_processor = EmailProcessor(self.credentials)
        
        # Initialize job tracker if provided, otherwise create a new one
        if job_tracker:
            self.job_tracker = job_tracker
        else:
            self.job_tracker = JobTracker()
        
        self.logger.info("EmailService initialized successfully")
    
    def _load_credentials(self) -> Dict[str, Any]:
        """
        Load Gmail API credentials.
        
        Returns:
            Loaded credentials
        """
        return init_google_credentials()
    
    def collect_questions_from_emails(
        self,
        sender_lists: Optional[List[str]] = None,
        limit: int = 1000,
        save_to_file: Optional[str] = None,
        since_timestamp: Optional[datetime] = None,
        timeout: int = 300
    ) -> pd.DataFrame:
        """
        Collect questions from emails and optionally save to a file.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            since_timestamp: Optional datetime to filter emails by timestamp
            timeout: Timeout in seconds for API requests (default: 300)
            
        Returns:
            DataFrame containing links and question content
        """
        if sender_lists is None:
            sender_lists = self.sender_lists
            
        # Collect questions from emails
        self.logger.info(f"Collecting questions from emails (limit: {limit})")
        
        # Start job tracking
        job_run_id = self.job_tracker.start_job("email_collection", {
            "sender_lists": sender_lists,
            "limit": limit,
            "since_timestamp": since_timestamp.isoformat() if since_timestamp else None
        })
        
        try:
            start_time = time.time()
            
            # Collect questions from emails
            email_questions = self.email_processor.collect_questions_from_emails(
                sender_lists=sender_lists,
                limit=limit,
                since_timestamp=since_timestamp,
                save_to_file=save_to_file,
                timeout=timeout
            )
            
            end_time = time.time()
        
            metrics = {
                "duration_seconds": end_time - start_time,
                "emails_processed": len(email_questions)
            }
            
            self.job_tracker.record_metrics(job_run_id, metrics)
            self.job_tracker.end_job(job_run_id, "completed")
            
            self.logger.info(f"Collected {len(email_questions)} questions from emails")
            
            return email_questions
            
        except Exception as e:
            self.logger.error(f"Error collecting questions from emails: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            return pd.DataFrame(columns=["link", "question_content"])
    
    def collect_questions_since_last_run(
        self,
        sender_lists: Optional[List[str]] = None,
        default_minutes: int = 1440,
        limit: int = 1000,
        save_to_file: Optional[str] = None,
        force_collection: bool = False,
        timeout: int = 900
    ) -> pd.DataFrame:
        """
        Collect questions from emails received since the last successful run.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            default_minutes: Default number of minutes to look back if no successful run is found
                             (typically this is set to days * 24 * 60 from the calling function)
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            force_collection: Whether to force collection regardless of last run timestamp
            timeout: Timeout in seconds for API requests (default: 900)
            
        Returns:
            DataFrame containing links and question content
        """
        if sender_lists is None:
            sender_lists = self.sender_lists
            
        self.logger.info(f"Collecting questions since last run (default: {default_minutes} minutes)")
        
        # Calculate days for better logging
        days = default_minutes / (24 * 60)
        self.logger.info(f"Looking back approximately {days:.1f} days")
        
        # If force_collection is True, ignore the last run timestamp
        if force_collection:
            since_timestamp = datetime.now() - timedelta(minutes=default_minutes)
            self.logger.info(f"Force collection enabled, using default: {default_minutes} minutes ({days:.1f} days)")
        else:
            # Get the timestamp of the last successful run
            last_run = self.job_tracker.get_last_successful_run("email_collection")
            
            if last_run and last_run.get("end_time"):
                try:
                    since_timestamp = datetime.fromisoformat(last_run["end_time"])
                    minutes_since = int((datetime.now() - since_timestamp).total_seconds() / 60)
                    days_since = minutes_since / (24 * 60)
                    self.logger.info(f"Last successful run: {since_timestamp.isoformat()} ({minutes_since} minutes / {days_since:.1f} days ago)")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error parsing last run timestamp: {str(e)}")
                    since_timestamp = datetime.now() - timedelta(minutes=default_minutes)
                    self.logger.warning(f"Could not parse last run timestamp, using default: {default_minutes} minutes ({days:.1f} days)")
            else:
                since_timestamp = datetime.now() - timedelta(minutes=default_minutes)
                self.logger.info(f"No previous run found, using default: {default_minutes} minutes ({days:.1f} days)")
        
        try:
            start_time = time.time()
            self.logger.info(f"Starting email collection with timeout={timeout}s")

            result = self.collect_questions_from_emails(
                sender_lists=sender_lists,
                limit=limit,
                save_to_file=save_to_file,
                since_timestamp=since_timestamp,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            self.logger.info(f"Email collection completed in {elapsed_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in collect_questions_since_last_run: {str(e)}", exc_info=True)
            self.logger.warning("Returning empty DataFrame due to error")
            return pd.DataFrame(columns=["link", "question_content"])
