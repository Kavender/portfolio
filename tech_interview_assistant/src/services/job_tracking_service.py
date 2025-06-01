from typing import Dict, Any, Optional, List
from utils.logger import get_logger
from data_manager.job_tracker import JobTracker


class JobTrackingService:
    """
    Service for handling job tracking operations.
    
    This service encapsulates functionality related to tracking jobs,
    recording metrics, and retrieving job history.
    """
    
    def __init__(
        self,
        db_path: str = "./src/data/job_tracker.db"
    ):
        """
        Initialize the JobTrackingService.
        
        Args:
            db_path: Path to the job tracker database
        """
        self.logger = get_logger("job_tracking_service")
        self.logger.info("Initializing JobTrackingService")
        
        # Initialize job tracker
        self.job_tracker = JobTracker(db_path=db_path)
        
        self.logger.info("JobTrackingService initialized successfully")
    
    def start_job(self, job_name: str, parameters: Dict[str, Any] = None) -> str:
        """
        Start a new job.
        
        Args:
            job_name: Name of the job
            parameters: Parameters for the job
            
        Returns:
            Job run ID
        """
        return self.job_tracker.start_job(job_name, parameters)
    
    def end_job(self, job_run_id: str, status: str) -> bool:
        """
        End a job.
        
        Args:
            job_run_id: Job run ID
            status: Status of the job
            
        Returns:
            True if successful, False otherwise
        """
        return self.job_tracker.end_job(job_run_id, status)
    
    def record_metrics(self, job_run_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Record metrics for a job.
        
        Args:
            job_run_id: Job run ID
            metrics: Metrics to record
            
        Returns:
            True if successful, False otherwise
        """
        return self.job_tracker.record_metrics(job_run_id, metrics)
    
    def get_job_run(self, job_run_id: str) -> Dict[str, Any]:
        """
        Get a job run by ID.
        
        Args:
            job_run_id: Job run ID
            
        Returns:
            Job run data
        """
        return self.job_tracker.get_job_run(job_run_id)
    
    def get_job_runs(self, job_name: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get job runs.
        
        Args:
            job_name: Name of the job to filter by
            limit: Maximum number of job runs to return
            
        Returns:
            List of job runs
        """
        return self.job_tracker.get_job_runs(job_name, limit)
    
    def get_last_successful_run(self, job_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the last successful run of a job.
        
        Args:
            job_name: Name of the job
            
        Returns:
            Last successful job run data, or None if not found
        """
        return self.job_tracker.get_last_successful_run(job_name)
    
    def get_job_metrics(self, job_run_id: str) -> Dict[str, Any]:
        """
        Get metrics for a job run.
        
        Args:
            job_run_id: Job run ID
            
        Returns:
            Job metrics
        """
        return self.job_tracker.get_job_metrics(job_run_id)
    
    def get_job_history(self, job_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the history of a job.
        
        Args:
            job_name: Name of the job
            limit: Maximum number of job runs to return
            
        Returns:
            List of job runs with metrics
        """
        job_runs = self.job_tracker.get_job_runs(job_name, limit)
        
        # Add metrics to each job run
        for job_run in job_runs:
            job_run["metrics"] = self.job_tracker.get_job_metrics(job_run["job_run_id"])
        
        return job_runs
    
    def get_job_summary(self, job_name: str, limit: int = 10) -> Dict[str, Any]:
        """
        Get a summary of a job.
        
        Args:
            job_name: Name of the job
            limit: Maximum number of job runs to return
            
        Returns:
            Job summary
        """
        job_runs = self.get_job_history(job_name, limit)
        
        # Calculate summary statistics
        total_runs = len(job_runs)
        successful_runs = sum(1 for run in job_runs if run["status"] == "completed")
        failed_runs = total_runs - successful_runs
        
        # Calculate average duration
        durations = []
        for run in job_runs:
            if "metrics" in run and "duration_seconds" in run["metrics"]:
                durations.append(run["metrics"]["duration_seconds"])
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Get the last run
        last_run = job_runs[0] if job_runs else None
        
        return {
            "job_name": job_name,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
            "avg_duration": avg_duration,
            "last_run": last_run
        }
