"""Logging Configuration - Structured logging with rotation and aggregation."""

import asyncio
import gzip
import json
import logging
import logging.handlers
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Any, Callable, TYPE_CHECKING
import asyncio
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

if TYPE_CHECKING:
    pass


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class LogConfig:
    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.JSON
    output: str = "stdout"
    file_path: str = "logs/erin.log"
    max_file_size_mb: int = 100
    backup_count: int = 10
    rotation: str = "daily"
    compression: bool = True
    include_timestamp: bool = True
    include_level: bool = True
    include_module: bool = True
    include_trace_id: bool = True
    sampling_rate: float = 1.0
    async_handling: bool = True
    buffer_size: int = 1000
    flush_interval: float = 1.0


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_trace_id: bool = True, include_module: bool = True):
        super().__init__()
        self.include_trace_id = include_trace_id
        self.include_module = include_module
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if self.include_trace_id:
            trace_id = getattr(record, "trace_id", None)
            if trace_id:
                log_entry["trace_id"] = trace_id
        
        if self.include_module:
            log_entry["module"] = record.module
            log_entry["function"] = record.funcName
            log_entry["line"] = record.lineno
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "levelname", "levelno", "pathname", 
                          "filename", "module", "lineno", "funcName", "created", 
                          "msecs", "relativeCreated", "thread", "threadName",
                          "processName", "process", "message", "exc_info", "exc_text",
                          "stack_info", "msg"]:
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """Structured logger with context management."""
    
    def __init__(self, name: str, config: LogConfig = None):
        self.name = name
        self.config = config or LogConfig()
        self._logger = logging.getLogger(name)
        self._context: Dict[str, Any] = {}
        self._setup_logger()
    
    def _setup_logger(self):
        self._logger.setLevel(getattr(logging, self.config.level.value))
        
        # Clear existing handlers
        for handler in self._logger.handlers[:]:
            self._logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if self.config.format == LogFormat.JSON:
            console_handler.setFormatter(StructuredFormatter(
                include_trace_id=self.config.include_trace_id,
                include_module=self.config.include_module,
            ))
        else:
            console_handler.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
        self._logger.addHandler(console_handler)
        
        # File handler if file path specified
        if self.config.file_path:
            file_path = Path(self.config.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.config.rotation == "daily":
                file_handler = TimedRotatingFileHandler(
                    self.config.file_path,
                    when="midnight",
                    interval=1,
                    backupCount=self.config.backup_count,
                    encoding="utf-8"
                )
            else:
                file_handler = RotatingFileHandler(
                    self.config.file_path,
                    maxBytes=self.config.max_file_size_mb * 1024 * 1024,
                    backupCount=self.config.backup_count,
                    encoding="utf-8"
                )
            
            if self.config.format == LogFormat.JSON:
                file_handler.setFormatter(StructuredFormatter(
                    include_trace_id=self.config.include_trace_id,
                    include_module=self.config.include_module,
                ))
            else:
                file_handler.setFormatter(logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                ))
            
            if self.config.compression:
                file_handler.namer = lambda name: name + ".gz"
                file_handler.rotator = self._compress_rotator
            
            self._logger.addHandler(file_handler)
    
    def _compress_rotator(self, source: str, dest: str):
        with open(source, "rb") as f_in:
            with gzip.open(dest, "wb") as f_out:
                f_out.write(f_in.read())
        os.remove(source)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method with context."""
        extra = {}
        for k, v in kwargs.items():
            if k not in ["exc_info", "stack_info", "stacklevel"]:
                extra[k] = v
        
        self._logger.log(level, message, extra=extra, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self._log(logging.ERROR, message, exc_info=True, **kwargs)
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Create a new logger with bound context."""
        new_logger = StructuredLogger(self.name, self.config)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def with_trace_id(self, trace_id: str) -> 'StructuredLogger':
        """Create logger with trace ID."""
        return self.bind(trace_id=trace_id)
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Create logger with additional context."""
        return self.bind(**kwargs)


class LogAggregator:
    """Aggregates logs from multiple sources."""
    
    def __init__(self, buffer_size: int = 10000, flush_interval: float = 5.0):
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self._buffer: List[Dict] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._handlers: List[Callable] = []
    
    def register_handler(self, handler: Callable[[Dict], None]):
        self._handlers.append(handler)
    
    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def log(self, entry: Dict):
        async with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= self.buffer_size:
                await self._flush()
    
    async def _flush_loop(self):
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self._flush()
    
    async def _flush(self):
        async with self._lock:
            if not self._buffer:
                return
            
            batch = self._buffer[:]
            self._buffer.clear()
        
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(batch)
                else:
                    handler(batch)
            except Exception as e:
                logger.error(f"Log handler failed: {e}")


class LogRotator:
    """Handles log file rotation and compression."""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self._lock = threading.Lock()
    
    def rotate(self, file_path: Path) -> Optional[Path]:
        """Rotate a log file."""
        with self._lock:
            if not file_path.exists():
                return None
            
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            rotated_path = file_path.with_suffix(f".{timestamp}{file_path.suffix}")
            
            try:
                file_path.rename(rotated_path)
            except Exception as e:
                logger.error(f"Failed to rotate log file: {e}")
                return None
            
            # Compress if enabled
            if self.config.compression:
                compressed_path = rotated_path.with_suffix(rotated_path.suffix + ".gz")
                with open(rotated_path, "rb") as f_in:
                    with gzip.open(compressed_path, "wb") as f_out:
                        f_out.write(f_in.read())
                rotated_path.unlink()
                return compressed_path
            
            return rotated_path
    
    def cleanup_old_logs(self, directory: Path, max_files: int = 10, max_age_days: int = 30):
        """Remove old log files."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        
        for file_path in sorted(Path(directory).glob("*.log*"), key=lambda p: p.stat().st_mtime):
            if file_path.stat().st_mtime < cutoff.timestamp() or len(list(Path(directory).glob("*.log*"))) > max_files:
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete old log {file_path}: {e}")


def create_logger(config: LogConfig = None) -> StructuredLogger:
    return StructuredLogger(config.name if config else "app", config)


def setup_logging(config: LogConfig = None) -> StructuredLogger:
    config = config or LogConfig()
    logger = StructuredLogger(config.name if config else "app", config)
    logging.getLogger().setLevel(getattr(logging, config.level.value))
    return logger