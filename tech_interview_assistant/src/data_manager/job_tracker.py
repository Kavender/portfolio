"""
Job Tracker for the Tech Interview Assistant.

This module provides functionality for tracking job execution,
recording metrics, and maintaining a history of job runs.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from data_manager.db_manager import DatabaseManager


class JobTracker:
    """
    Tracks job execution and records metrics.
    
    This class provides methods for starting and ending job runs,
    recording metrics, and querying job history.
    """
    
    def __init__(self, db_path: str = "./src/data/job_tracker.db"):
        """
        Initialize the JobTracker.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_manager = DatabaseManager(db_path)
        self.active_jobs = {}
    
    def start_job(self, job_name: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Start a job and record its start time.
        
        Args:
            job_name: Name of the job
            metadata: Optional metadata about the job
            
        Returns:
            ID of the job run
        """
        job_run_id = self.db_manager.start_job_run(job_name, metadata)
        self.active_jobs[job_run_id] = time.time()
        return job_run_id
    
    def end_job(self, job_run_id: int, status: str = "completed") -> Dict[str, Any]:
        """
        End a job and record its end time and duration.
        
        Args:
            job_run_id: ID of the job run
            status: Status of the job run (completed, failed, etc.)
            
        Returns:
            Dictionary with job metrics
        """
        if job_run_id not in self.active_jobs:
            raise ValueError(f"Job run {job_run_id} is not active")
        
        start_time = self.active_jobs[job_run_id]
        duration = time.time() - start_time
        
        self.db_manager.end_job_run(job_run_id, status)
        self.db_manager.record_metric(job_run_id, "duration_seconds", duration)
        
        del self.active_jobs[job_run_id]
        
        return {"job_run_id": job_run_id, "duration_seconds": duration}
    
    def record_metrics(self, job_run_id: int, metrics: Dict[str, Any]) -> None:
        """
        Record metrics for a job run.
        
        Args:
            job_run_id: ID of the job run
            metrics: Dictionary of metrics to record
        """
        for metric_name, metric_value in metrics.items():
            self.db_manager.record_metric(job_run_id, metric_name, metric_value)
    
    def get_last_successful_run(self, job_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the last successful run of a job.
        
        Args:
            job_name: Name of the job
            
        Returns:
            Dictionary with job run information or None if no successful run found
        """
        return self.db_manager.get_last_successful_run(job_name)
    
    def get_job_history(self, job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the history of a job.
        
        Args:
            job_name: Name of the job
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries with job run information
        """
        return self.db_manager.get_job_history(job_name, limit)
    
    def get_timestamp_since_last_run(self, job_name: str, default_minutes: int = 60) -> datetime:
        """
        Get a timestamp representing the time since the last successful run.
        If no successful run is found, returns the current time minus default_minutes.
        
        Args:
            job_name: Name of the job
            default_minutes: Default number of minutes to subtract if no successful run is found
            
        Returns:
            Timestamp representing the time since the last successful run
        """
        last_run = self.get_last_successful_run(job_name)
        
        if last_run and last_run.get("end_time"):
            try:
                return datetime.fromisoformat(last_run["end_time"])
            except (ValueError, TypeError):
                pass
        
        # If no successful run is found or the timestamp is invalid,
        # return the current time minus default_minutes
        return datetime.now() - timedelta(minutes=default_minutes)
    
    def run_job(self, job_name: str, job_func, *args, **kwargs) -> Dict[str, Any]:
        """
        Run a job and track its execution.
        
        Args:
            job_name: Name of the job
            job_func: Function to run
            *args: Arguments to pass to the job function
            **kwargs: Keyword arguments to pass to the job function
            
        Returns:
            Dictionary with job metrics
        """
        metadata = kwargs.pop("metadata", None)
        job_run_id = self.start_job(job_name, metadata)
        
        try:
            start_time = time.time()
            result = job_func(*args, **kwargs)
            end_time = time.time()
            
            # Record metrics
            metrics = {
                "duration_seconds": end_time - start_time
            }
            
            if isinstance(result, dict):
                for key, value in result.items():
                    if key != "result" and isinstance(value, (int, float, str, bool)):
                        metrics[key] = value
            
            self.record_metrics(job_run_id, metrics)
            self.end_job(job_run_id, "completed")
            
            return {
                "job_run_id": job_run_id,
                "status": "completed",
                "metrics": metrics,
                "result": result
            }
            
        except Exception as e:
            self.record_metrics(job_run_id, {"error": str(e)})
            self.end_job(job_run_id, "failed")
            
            return {
                "job_run_id": job_run_id,
                "status": "failed",
                "error": str(e)
            }
