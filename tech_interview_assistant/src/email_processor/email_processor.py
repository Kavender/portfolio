from typing import List, Dict, Any, Optional
import os
import re
import pandas as pd
from datetime import datetime
from langchain_core.messages import HumanMessage
from src.utils.logger import get_logger
from src.email_processor.gmail_utils import read_emails_from_senders


class EmailProcessor:
    """
    Class for processing emails to extract questions and links.
    """
    
    def __init__(self, credentials):
        """
        Initialize the EmailProcessor with Google API credentials.
        
        Args:
            credentials: Google API credentials for accessing Gmail
        """
        self.credentials = credentials
        self.logger = get_logger("email_processor")
    
    def collect_questions_from_emails(
        self,
        sender_lists: List[str],
        limit: int = 100,
        since_timestamp: Optional[datetime] = None,
        save_to_file: Optional[str] = None,
        timeout: int = 900
    ) -> pd.DataFrame:
        """
        Collect questions from emails sent by specified senders.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            limit: Maximum number of emails to process
            since_timestamp: Optional datetime to filter emails by timestamp
            save_to_file: Optional file path to save the results
            timeout: Timeout in seconds for API requests (default: 900)
                        
        Returns:
            DataFrame containing links and question content
        """
        # Fetch emails from the specified senders
        self.logger.info(f"Fetching emails from {sender_lists} (limit: {limit})")
        if since_timestamp:
            self.logger.info(f"Filtering emails since {since_timestamp.isoformat()}")
            
        emails = read_emails_from_senders(
            credentials=self.credentials,
            sender_addresses=sender_lists,
            limit=limit,
            since_timestamp=since_timestamp,
            timeout=timeout
        )
        
        # Check if emails is a string (error message) or a list
        if isinstance(emails, str):
            self.logger.error(f"Error fetching emails: {emails}")
            return pd.DataFrame(columns=["link", "question_content"])
        
        self.logger.info(f"Processing {len(emails)} emails")
        
        links = []
        for email in emails:
            # Check if email is a dictionary with the expected keys
            if not isinstance(email, dict) or "body" not in email:
                self.logger.warning(f"Skipping invalid email format")
                continue
                
            email_content = email["body"]
            question_match_pattern = r"[-]{80}\s+(.*?)(?=\n[-]{80})"
            solution_link_match = re.search(
                r'\[(https://www\.interviewquery\.com/questions/.+?solution=true).+?\]', 
                email_content
            )
            
            # Extract question content
            question_matches = re.findall(question_match_pattern, email_content, re.DOTALL)
            question = ""
            for match in question_matches:
                question += match.strip()
                
            # Clean up question if needed
            if "Need a hint first?" in question:
                question, _ = question.split("Need a hint first", 1)
            
            question_page_link = solution_link_match.group(1) if solution_link_match else "Solution link not found."
            
            links.append((question_page_link, question))
        
        # Create DataFrame
        df = pd.DataFrame(links, columns=["link", "question_content"])
        
        # Save to file if specified
        if save_to_file and not df.empty:
            self.logger.info(f"Saving {len(df)} questions to {save_to_file}")
            try:
                os.makedirs(os.path.dirname(save_to_file), exist_ok=True)
                df.to_csv(save_to_file, index=False)
            except Exception as e:
                self.logger.error(f"Error saving to file: {str(e)}")
        
        return df
    
    def collect_questions_since_last_run(
        self,
        sender_lists: List[str],
        last_run_timestamp: datetime,
        limit: int = 1000,
        save_to_file: Optional[str] = None,
        timeout: int = 900  # Increased from 300 to 900
    ) -> pd.DataFrame:
        """
        Collect questions from emails received since the last successful run.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            last_run_timestamp: Timestamp of the last successful run
            limit: Maximum number of emails to process
            save_to_file: Optional file path to save the results
            timeout: Timeout in seconds for API requests (default: 900)
            
        Returns:
            DataFrame containing links and question content
        """
        self.logger.info(f"Collecting questions since {last_run_timestamp.isoformat()}")
        
        return self.collect_questions_from_emails(
            sender_lists=sender_lists,
            limit=limit,
            since_timestamp=last_run_timestamp,
            save_to_file=save_to_file,
            timeout=timeout
        )
    
    def format_question_for_solver(self, question_content: str) -> Dict[str, Any]:
        """
        Format a question for the solver.
        
        Args:
            question_content: The raw question content
            
        Returns:
            Dictionary with the formatted question ready for the solver
        """
        return {"messages": [HumanMessage(content=question_content)]}
