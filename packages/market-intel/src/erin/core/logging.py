"""ERIN Core Logging."""

import logging
import logging.config
import sys
import json
import os
from datetime import datetime
from typing import Any, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, "trace_id"):
            record.__dict__["trace_id"] = record.trace_id
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "args", "exc_info",
                "exc_text", "stack_info", "msg"
            ]:
                if not key.startswith("_"):
                    setattr(record, key, value)
        
        return json.dumps(record.__dict__, default=str)


def setup_logging(
    level: str = "INFO",
    log_file: str = "logs/erin.log",
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 10,
) -> None:
    """Setup application logging."""
    
    # Create logs directory
    log_dir = os.path.dirname(os.path.abspath("logs/erin.log"))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper()))
    
    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    if os.environ.get("LOG_FORMAT", "json").lower() == "json":
        console_handler.setFormatter(JsonFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    # File handler
    log_dir = os.path.dirname(os.path.abspath("logs/erin.log"))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        filename="logs/erin.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8",
    )
    
    if os.environ.get("LOG_FORMAT", "json").lower() == "json":
        file_handler.setFormatter(JsonFormatter())
    else:
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
    
    # Configure root logger
    logging.root.handlers = [console_handler, file_handler]
    logging.root.setLevel(logging.INFO)
    
    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields
        if hasattr(record, "trace_id"):
            record.__dict__["trace_id"] = record.trace_id
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "lineno", "funcName", "created",
                "msecs", "relativeCreated", "thread", "threadName",
                "processName", "process", "message", "exc_info", "exc_text",
                "stack_info", "msg"
            ]:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)


def get_logger(name: str) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)