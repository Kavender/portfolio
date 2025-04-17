import re
import pandas as pd
from typing import List, Dict, Any, Optional, Union, Callable

class DataTransformer:
    """
    Class for transforming data.
    """
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing extra whitespace and normalizing line endings.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n+', '\n', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r' +', ' ', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        return text
    
    @staticmethod
    def remove_markdown(text: str) -> str:
        """
        Remove markdown formatting from text.
        
        Args:
            text: Text to clean
            
        Returns:
            Text without markdown formatting
        """
        if not text:
            return ""
        
        # Remove code blocks
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
        # Remove inline code
        text = re.sub(r'`.*?`', '', text)
        
        # Remove headers
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
        # Remove bold/italic
        text = re.sub(r'\*\*?(.*?)\*\*?', r'\1', text)
        
        # Remove links
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        
        # Clean up whitespace
        return DataTransformer.clean_text(text)
    
    @staticmethod
    def extract_code_from_markdown(text: str) -> str:
        """
        Extract code blocks from markdown text.
        
        Args:
            text: Markdown text
            
        Returns:
            Extracted code
        """
        if not text:
            return ""
        
        # Extract code blocks
        code_blocks = re.findall(r'```(?:python)?\s*\n(.*?)\n```', text, re.DOTALL)
        
        # Join code blocks with newlines
        return '\n\n'.join(code_blocks)
    
    @staticmethod
    def apply_to_dataframe(
        df: pd.DataFrame, 
        column: str, 
        function: Callable, 
        new_column: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Apply a function to a column in a DataFrame.
        
        Args:
            df: DataFrame to transform
            column: Column to apply the function to
            function: Function to apply
            new_column: Name of the new column (if None, overwrites the original column)
            
        Returns:
            Transformed DataFrame
        """
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        if new_column:
            df[new_column] = df[column].apply(function)
        else:
            df[column] = df[column].apply(function)
        
        return df
    
    @staticmethod
    def filter_dataframe(
        df: pd.DataFrame, 
        column: str, 
        condition: Callable[[Any], bool]
    ) -> pd.DataFrame:
        """
        Filter a DataFrame based on a condition.
        
        Args:
            df: DataFrame to filter
            column: Column to apply the condition to
            condition: Function that returns True for rows to keep
            
        Returns:
            Filtered DataFrame
        """
        if column not in df.columns:
            raise ValueError(f"Column '{column}' not found in DataFrame")
        
        return df[df[column].apply(condition)]
    
    @staticmethod
    def merge_dataframes(
        df1: pd.DataFrame, 
        df2: pd.DataFrame, 
        on: Union[str, List[str]], 
        how: str = 'inner'
    ) -> pd.DataFrame:
        """
        Merge two DataFrames.
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            on: Column(s) to merge on
            how: Type of merge ('inner', 'outer', 'left', or 'right')
            
        Returns:
            Merged DataFrame
        """
        return pd.merge(df1, df2, on=on, how=how)
