import os
import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from langchain_community.utilities.sql_database import SQLDatabase


class DataManager:
    """
    Class for managing data storage and retrieval.
    """
    
    def __init__(self, data_dir: str = "./src/data"):
        """
        Initialize the DataManager.
        
        Args:
            data_dir: Directory for data storage
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_to_csv(self, df: pd.DataFrame, filename: str, index: bool = False) -> str:
        """
        Save a DataFrame to a CSV file.
        
        Args:
            df: DataFrame to save
            filename: Name of the file (without path)
            index: Whether to include the index
            
        Returns:
            Full path to the saved file
        """
        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=index)
        return filepath
    
    def load_from_csv(self, filename: str, **kwargs) -> pd.DataFrame:
        """
        Load a DataFrame from a CSV file.
        
        Args:
            filename: Name of the file (without path)
            **kwargs: Additional arguments to pass to pd.read_csv
            
        Returns:
            Loaded DataFrame
        """
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        df = pd.read_csv(filepath, **kwargs)
        return df
    
    def initialize_db_connection(self, db_name: str) -> Tuple[Any, sqlite3.Connection]:
        """
        Initialize a connection to a SQLite database.
        
        Args:
            db_name: Name of the database
            
        Returns:
            Tuple of (SQLDatabase object, sqlite3.Connection)
        """
        
        # If db_name doesn't have a path, add the data directory
        if not os.path.dirname(db_name):
            db_path = os.path.join(self.data_dir, db_name)
        else:
            db_path = db_name

        db = SQLDatabase.from_uri(F"sqlite:///{db_path}")
        conn = sqlite3.connect(db_name)
        return db, conn
    
    def save_to_db(
        self, 
        df: pd.DataFrame, 
        table_name: str, 
        db_name: str, 
        if_exists: str = 'replace'
    ) -> None:
        """
        Save a DataFrame to a SQLite database.
        
        Args:
            df: DataFrame to save
            table_name: Name of the table
            db_name: Name of the database
            if_exists: What to do if the table exists ('fail', 'replace', or 'append')
        """
        if not os.path.dirname(db_name):
            db_path = os.path.join(self.data_dir, db_name)
        else:
            db_path = db_name

        conn = sqlite3.connect(db_path)
        df.to_sql(name=table_name, con=conn, if_exists=if_exists, index=False)
        conn.close()
    
    def load_from_db(
        self, 
        query: str, 
        db_name: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Load data from a SQLite database using a query.
        
        Args:
            query: SQL query
            db_name: Name of the database
            params: Parameters for the query
            
        Returns:
            DataFrame with query results
        """
        if not os.path.dirname(db_name):
            db_path = os.path.join(self.data_dir, db_name)
        else:
            db_path = db_name
        
        conn = sqlite3.connect(db_path)

        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Name of the file (without path)
            
        Returns:
            True if the file exists, False otherwise
        """
        filepath = os.path.join(self.data_dir, filename)
        return os.path.exists(filepath)
    
    def get_file_path(self, filename: str) -> str:
        """
        Get the full path to a file.
        
        Args:
            filename: Name of the file (without path)
            
        Returns:
            Full path to the file
        """
        return os.path.join(self.data_dir, filename)
