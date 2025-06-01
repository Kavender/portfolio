from typing import List, Tuple
import time
from selenium import webdriver
from utils.utils import (
    batch,
    clean_extracted_text,
    extract_question_from_url,
    hash_text_to_digits
)
from utils.logger import default_logger as logger
from utils.retrieval_utils import login_to_interview_query, extract_content_from_tab


class WebScraper:
    """
    Class for scraping content from web pages, specifically Interview Query.
    """
    
    def __init__(self, login_page_url: str, login_page_button: str):
        """
        Initialize the WebScraper with login information.
        
        Args:
            login_page_url: URL of the login page
            login_page_button: CSS selector for the login button
        """
        self.login_page_url = login_page_url
        self.login_page_button = login_page_button
        self.driver = None
    
    def initialize_driver(self):
        """
        Initialize the Selenium WebDriver.
        
        Returns:
            Initialized WebDriver
        """
        if self.driver is None:
            self.driver = webdriver.Chrome()
            self.login()
        return self.driver
    
    def login(self):
        """
        Log in to Interview Query.
        """
        if self.driver is not None:
            login_to_interview_query(
                self.driver, 
                self.login_page_url, 
                self.login_page_button
            )
    
    def is_placeholder_content(self, content: str) -> bool:
        """
        Check if the content is placeholder text.
        
        Args:
            content: Content to check
            
        Returns:
            True if the content is placeholder text, False otherwise
        """
        import re
        
        # Common placeholder phrases
        placeholder_phrases = [
            "Lorem ipsum dolor sit amet",
            "consectetur adipiscing elit",
            "eiusmod tempor incididunt",
            "sunt in culpa qui officia deserunt"
        ]
        
        # Check if any of the placeholder phrases are in the content
        for phrase in placeholder_phrases:
            if re.search(re.escape(phrase), content, re.IGNORECASE):
                return True
        return False
    
    def extract_qa_from_link(
        self, 
        link: str, 
        button_texts: List[str]
    ) -> Tuple[str, str, str, str, str]:
        """
        Extract question and solution content from a link.
        
        Args:
            link: URL to extract content from
            button_texts: List of button texts to remove from content
            
        Returns:
            Tuple of (hash_id, link, question_abbr, question_content, solution_content)
        """
        try:
            driver = self.initialize_driver()
            driver.get(link)
            
            # Extract question abbreviation from URL
            question_abbr = extract_question_from_url(link)
            logger.info(f"Navigating to page: {link}")
            
            # Generate hash ID
            hash_id = hash_text_to_digits(question_abbr, num_digits=4)
            
            # Extract question content
            question_content = extract_content_from_tab(driver=driver, tab_name="Question")
            question_content = clean_extracted_text(question_content, button_texts)
            
            # Extract solution content
            solution_content = extract_content_from_tab(driver=driver, tab_name="Solution")
            
            # Check if solution is placeholder
            if self.is_placeholder_content(solution_content):
                solution_content = ""
                self.login()
            
            logger.info("Question Content:", question_content[:100] + "..." if len(question_content) > 100 else question_content)
            logger.info("Solution Content:", solution_content[:100] + "..." if len(solution_content) > 100 else solution_content)
            
            # Add delay to avoid rate limiting
            time.sleep(5)
            
            return hash_id, link, question_abbr, question_content, solution_content
            
        except Exception as e:
            logger.error(f"{link} is unavailable to extract: {e}")
            return "", link, "", "", ""
    
    def extract_qa_batch(
        self, 
        links: List[str], 
        button_texts: List[str], 
        batch_size: int = 5
    ) -> List[List[str]]:
        """
        Extract question and solution content from a batch of links.
        
        Args:
            links: List of URLs to extract content from
            button_texts: List of button texts to remove from content
            batch_size: Number of links to process in each batch
            
        Returns:
            List of [hash_id, link, question_abbr, question_content, solution_content] for each link
        """
        all_qa_extracted = []
        
        for batch_links in batch(links, batch_size=batch_size):
            batch_qa_extracted = []
            
            for link in batch_links:
                result = self.extract_qa_from_link(link, button_texts)
                if result[0]:  # If hash_id is not empty
                    batch_qa_extracted.append(list(result))
            
            all_qa_extracted.extend(batch_qa_extracted)
        
        return all_qa_extracted
    
    def close(self):
        """
        Close the WebDriver.
        """
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
