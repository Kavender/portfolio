from typing import List, Optional
import pandas as pd
from src.data_manager.job_tracker import JobTracker
from src.data_manager.data_manager import DataManager
from src.utils.logger import get_logger
from src.utils.web_scraper import WebScraper


class DataService:
    """
    Service for handling data operations.
    
    This service encapsulates functionality related to data management,
    including loading and saving data, and web scraping.
    """
    
    def __init__(
        self,
        job_tracker: Optional[JobTracker] = None
    ):
        """
        Initialize the DataService.
        
        Args:
            job_tracker: JobTracker instance for tracking jobs
        """
        self.logger = get_logger("data_service")
        self.logger.info("Initializing DataService")
        
        # Initialize components
        self.data_manager = DataManager()
        
        # Initialize job tracker if provided, otherwise create a new one
        if job_tracker:
            self.job_tracker = job_tracker
        else:
            self.job_tracker = JobTracker()
        
        self.logger.info("DataService initialized successfully")
    
    def load_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load data from a CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            DataFrame containing the loaded data
        """
        try:
            return self.data_manager.load_from_csv(file_path)
        except Exception as e:
            self.logger.error(f"Error loading from CSV: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    def save_to_csv(self, data: pd.DataFrame, file_path: str) -> bool:
        """
        Save data to a CSV file.
        
        Args:
            data: DataFrame to save
            file_path: Path to the CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.data_manager.save_to_csv(data, file_path)
            return True
        except Exception as e:
            self.logger.error(f"Error saving to CSV: {str(e)}", exc_info=True)
            return False
    
    def scrape_questions(
        self, 
        urls: List[str], 
        batch_size: int = 5, 
        save_to_file: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Scrape questions and solutions from provided URLs.
        
        Args:
            urls: List of URLs to scrape
            batch_size: Number of URLs to process in each batch
            save_to_file: Optional file path to save the results
            
        Returns:
            DataFrame containing scraped questions and solutions
        """
        # Start job tracking
        job_run_id = self.job_tracker.start_job("web_scraping", {
            "num_urls": len(urls),
            "batch_size": batch_size
        })
        
        try:
            # Initialize web scraper
            login_page_url = "https://www.interviewquery.com/login"
            login_page_button = "div.button_inner__6ximl.button_center__HXCC_"
            web_scraper = WebScraper(login_page_url, login_page_button)
            question_page_button_texts = ['I need help', "I've got an answer", 'Show solution']
            
            try:
                # Extract questions and solutions in batches
                qa_extracted = web_scraper.extract_qa_batch(
                    urls, 
                    question_page_button_texts, 
                    batch_size=batch_size
                )
                
                # Convert to DataFrame
                columns = ["id_question", "url", "question_abbr", "question_content", "solution_content"]
                df_qa_extracted = pd.DataFrame(qa_extracted, columns=columns)
                
                # Save to file if specified
                if save_to_file:
                    self.save_to_csv(df_qa_extracted, save_to_file)
                
                # Record metrics
                metrics = {
                    "urls_processed": len(urls),
                    "questions_scraped": len(df_qa_extracted)
                }
                
                self.job_tracker.record_metrics(job_run_id, metrics)
                self.job_tracker.end_job(job_run_id, "completed")
                
                self.logger.info(f"Scraped {len(df_qa_extracted)} questions from {len(urls)} URLs")
                
                return df_qa_extracted
                
            finally:
                # Clean up
                web_scraper.close()
                
        except Exception as e:
            self.logger.error(f"Error scraping questions: {str(e)}", exc_info=True)
            self.job_tracker.record_metrics(job_run_id, {"error": str(e)})
            self.job_tracker.end_job(job_run_id, "failed")
            
            # Return empty DataFrame
            return pd.DataFrame(columns=["id_question", "url", "question_abbr", "question_content", "solution_content"])
