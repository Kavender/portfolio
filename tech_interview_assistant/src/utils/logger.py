from typing import Dict, Any, Optional, Union
import os
import sys
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


class StructuredLogFormatter(logging.Formatter):
    """
    Custom formatter for structured logging.
    
    This formatter outputs logs in a structured format (JSON)
    to make them easier to parse and analyze.
    """
    
    def __init__(self, include_context: bool = True):
        """
        Initialize the formatter.
        
        Args:
            include_context: Whether to include context information in the logs
        """
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log record as a JSON string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        
        # Include exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Include context information if available and enabled
        if self.include_context and hasattr(record, "context"):
            log_data["context"] = record.context
        
        # Include any extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno", 
                          "lineno", "module", "msecs", "message", "msg", "name", 
                          "pathname", "process", "processName", "relativeCreated", 
                          "stack_info", "thread", "threadName", "context"]:
                log_data[key] = value
        
        return json.dumps(log_data)


class ContextAdapter(logging.LoggerAdapter):
    """
    Adapter for adding context to log records.
    
    This adapter allows adding context information to log records
    without modifying the logger itself.
    """
    
    def process(self, msg, kwargs):
        """
        Process the log record by adding context information.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments for the log record
            
        Returns:
            Tuple of (msg, kwargs) with context information added
        """
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        
        if hasattr(self, "context"):
            kwargs["extra"]["context"] = self.context
        
        return msg, kwargs


def setup_logger(
    name: str = "tech_interview_assistant",
    log_dir: str = "./src/logs",
    log_level: int = logging.INFO,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    structured_logging: bool = True
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Name of the logger
        log_dir: Directory to store log files
        log_level: Logging level
        console_output: Whether to output logs to the console
        file_output: Whether to output logs to a file
        max_bytes: Maximum size of log files before rotation
        backup_count: Number of backup log files to keep
        structured_logging: Whether to use structured logging
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    if structured_logging:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Add file handler if enabled
    if file_output:
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, f"{name}.log"),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(
    name: str = "tech_interview_assistant",
    context: Optional[Dict[str, Any]] = None
) -> Union[logging.Logger, ContextAdapter]:
    """
    Get a logger with the specified name and context.
    
    Args:
        name: Name of the logger
        context: Context information to add to log records
        
    Returns:
        Logger or ContextAdapter with the specified name and context
    """
    logger = logging.getLogger(name)
    
    if context:
        adapter = ContextAdapter(logger, {})
        adapter.context = context
        return adapter
    
    return logger


# Create a default logger
default_logger = setup_logger()
