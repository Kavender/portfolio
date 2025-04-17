import re
import pandas as pd
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from src.utils.gmail_utils import read_emails_from_senders
from ipdb import set_trace

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
    
    def collect_questions_from_emails(self, sender_lists: List[str], limit: int = 1000) -> pd.DataFrame:
        """
        Collect questions from emails sent by specified senders.
        
        Args:
            sender_lists: List of sender email addresses to filter by
            limit: Maximum number of emails to process
            
        Returns:
            DataFrame containing links and question content
        """
        # Fetch emails from the specified senders
        emails = read_emails_from_senders(
            credentials=self.credentials,
            sender_addresses=sender_lists,
            limit=limit
        )
        
        # Check if emails is a string (error message) or a list
        if isinstance(emails, str):
            print(f"Error fetching emails: {emails}")
            return pd.DataFrame(columns=["link", "question_content"])
        
        print(f"Processed {len(emails)} emails")
        
        links = []
        for email in emails:
            # Check if email is a dictionary with the expected keys
            if not isinstance(email, dict) or "body" not in email:
                print(f"Skipping invalid email format: {email}")
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
        
        return pd.DataFrame(links, columns=["link", "question_content"])
    
    def format_question_for_solver(self, question_content: str) -> Dict[str, Any]:
        """
        Format a question for the solver.
        
        Args:
            question_content: The raw question content
            
        Returns:
            Dictionary with the formatted question ready for the solver
        """
        return {"messages": [HumanMessage(content=question_content)]}
