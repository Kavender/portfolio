"""
Database Manager for the Tech Interview Assistant.

This module provides functionality for managing the SQLite database
used to track job execution history and metrics.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple


class DatabaseManager:
    """
    Manages the SQLite database for job tracking.
    
    This class provides methods for creating, querying, and updating
    the database used to track job execution history and metrics.
    """
    
    def __init__(self, db_path: str = "./src/data/job_tracker.db"):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the database
        self._init_db()
    
    def _init_db(self) -> None:
        """
        Initialize the database schema if it doesn't exist.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create job_runs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            status TEXT NOT NULL,
            metadata TEXT
        )
        ''')
        
        # Create job_metrics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_run_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value TEXT NOT NULL,
            FOREIGN KEY (job_run_id) REFERENCES job_runs (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a connection to the SQLite database.
        
        Returns:
            SQLite connection object
        """
        return sqlite3.connect(self.db_path)
    
    def start_job_run(self, job_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Record the start of a job run.
        
        Args:
            job_name: Name of the job
            metadata: Optional metadata about the job
            
        Returns:
            ID of the job run
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute(
            "INSERT INTO job_runs (job_name, start_time, status, metadata) VALUES (?, ?, ?, ?)",
            (job_name, datetime.now().isoformat(), "running", metadata_json)
        )
        
        job_run_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return job_run_id
    
    def end_job_run(self, job_run_id: int, status: str = "completed") -> None:
        """
        Record the end of a job run.
        
        Args:
            job_run_id: ID of the job run
            status: Status of the job run (completed, failed, etc.)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE job_runs SET end_time = ?, status = ? WHERE id = ?",
            (datetime.now().isoformat(), status, job_run_id)
        )
        
        conn.commit()
        conn.close()
    
    def record_metric(self, job_run_id: int, metric_name: str, metric_value: Any) -> None:
        """
        Record a metric for a job run.
        
        Args:
            job_run_id: ID of the job run
            metric_name: Name of the metric
            metric_value: Value of the metric
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Convert metric value to string if it's not already
        if not isinstance(metric_value, str):
            metric_value = str(metric_value)
        
        cursor.execute(
            "INSERT INTO job_metrics (job_run_id, metric_name, metric_value) VALUES (?, ?, ?)",
            (job_run_id, metric_name, metric_value)
        )
        
        conn.commit()
        conn.close()
    
    def get_last_successful_run(self, job_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the last successful run of a job.
        
        Args:
            job_name: Name of the job
            
        Returns:
            Dictionary with job run information or None if no successful run found
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, start_time, end_time, metadata
            FROM job_runs
            WHERE job_name = ? AND status = 'completed'
            ORDER BY end_time DESC
            LIMIT 1
            """,
            (job_name,)
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        job_run_id, start_time, end_time, metadata_json = row
        
        return {
            "id": job_run_id,
            "start_time": start_time,
            "end_time": end_time,
            "metadata": json.loads(metadata_json) if metadata_json else None
        }
    
    def get_job_metrics(self, job_run_id: int) -> Dict[str, Any]:
        """
        Get metrics for a job run.
        
        Args:
            job_run_id: ID of the job run
            
        Returns:
            Dictionary of metrics
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT metric_name, metric_value FROM job_metrics WHERE job_run_id = ?",
            (job_run_id,)
        )
        
        metrics = {}
        for metric_name, metric_value in cursor.fetchall():
            # Try to convert to appropriate type
            try:
                # Try to convert to int
                metrics[metric_name] = int(metric_value)
            except ValueError:
                try:
                    # Try to convert to float
                    metrics[metric_name] = float(metric_value)
                except ValueError:
                    # Keep as string
                    metrics[metric_name] = metric_value
        
        conn.close()
        return metrics
    
    def get_job_history(self, job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the history of a job.
        
        Args:
            job_name: Name of the job
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries with job run information
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, start_time, end_time, status, metadata
            FROM job_runs
            WHERE job_name = ?
            ORDER BY start_time DESC
            LIMIT ?
            """,
            (job_name, limit)
        )
        
        job_runs = []
        for job_run_id, start_time, end_time, status, metadata_json in cursor.fetchall():
            job_run = {
                "id": job_run_id,
                "start_time": start_time,
                "end_time": end_time,
                "status": status,
                "metadata": json.loads(metadata_json) if metadata_json else None
            }
            
            # Get metrics for this job run
            job_run["metrics"] = self.get_job_metrics(job_run_id)
            
            job_runs.append(job_run)
        
        conn.close()
        return job_runs
