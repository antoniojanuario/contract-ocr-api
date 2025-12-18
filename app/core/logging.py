"""
Comprehensive logging configuration for the application
"""
import logging
import logging.handlers
import sys
import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        
        # Add document ID if available
        if hasattr(record, 'document_id'):
            log_data["document_id"] = record.document_id
        
        # Add error details if available
        if hasattr(record, 'error_code'):
            log_data["error_code"] = record.error_code
        
        if hasattr(record, 'error_category'):
            log_data["error_category"] = record.error_category
        
        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, ensure_ascii=False)


class PlainFormatter(logging.Formatter):
    """Human-readable formatter for development"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build the base message
        base_message = record.getMessage()
        message = f"{timestamp} - {record.name} - {record.levelname} - {base_message}"
        
        # Only add structured information if it's not already in the message
        # (to avoid duplication when ErrorLogger already formatted it)
        if hasattr(record, 'request_id') and f"[req:{record.request_id[:8]}]" not in base_message:
            message += f" [req:{record.request_id[:8]}]"
        
        if hasattr(record, 'document_id') and f"[doc:{record.document_id[:8]}]" not in base_message:
            message += f" [doc:{record.document_id[:8]}]"
        
        if hasattr(record, 'error_code') and f"[error:{record.error_code}]" not in base_message:
            message += f" [error:{record.error_code}]"
        
        # Add exception information if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


class ErrorLogger:
    """Specialized logger for error tracking and alerting"""
    
    def __init__(self):
        self.logger = logging.getLogger("error_tracker")
        self.error_counts = {}
        self.last_alert_time = {}
    
    def log_error(
        self,
        error_code: str,
        message: str,
        category: str = "unknown",
        request_id: Optional[str] = None,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        exc_info: Optional[tuple] = None
    ):
        """Log an error with structured information"""
        # Build structured message with all information
        structured_message = message
        
        # Add structured information to the message itself for better visibility
        message_parts = [structured_message]
        
        if request_id:
            message_parts.append(f"[req:{request_id[:8]}]")
        
        if document_id:
            message_parts.append(f"[doc:{document_id[:8]}]")
        
        if user_id:
            message_parts.append(f"[user:{user_id}]")
        
        if details:
            # Include key details in the message
            detail_parts = []
            for key, value in details.items():
                if isinstance(value, (str, int, float, bool)):
                    detail_parts.append(f"{key}:{value}")
            if detail_parts:
                message_parts.append(f"[details:{','.join(detail_parts)}]")
        
        message_parts.append(f"[error:{error_code}]")
        
        final_message = " ".join(message_parts)
        
        # Also prepare extra data for structured logging
        extra_data = {
            "error_code": error_code,
            "error_category": category,
            "details": details or {}
        }
        
        if request_id:
            extra_data["request_id"] = request_id
        
        if document_id:
            extra_data["document_id"] = document_id
        
        if user_id:
            extra_data["user_id"] = user_id
        
        # Create log record with extra data
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=logging.ERROR,
            fn="",
            lno=0,
            msg=final_message,
            args=(),
            exc_info=exc_info
        )
        
        # Add extra attributes for structured logging systems
        for key, value in extra_data.items():
            setattr(record, key, value)
        
        self.logger.handle(record)
        
        # Track error frequency for alerting
        self._track_error_frequency(error_code)
    
    def _track_error_frequency(self, error_code: str):
        """Track error frequency for alerting purposes"""
        now = datetime.utcnow()
        
        # Initialize tracking for new error codes
        if error_code not in self.error_counts:
            self.error_counts[error_code] = {"count": 0, "first_seen": now, "last_seen": now}
        
        # Update counts
        self.error_counts[error_code]["count"] += 1
        self.error_counts[error_code]["last_seen"] = now
        
        # Check if we should send an alert (simple threshold-based alerting)
        count = self.error_counts[error_code]["count"]
        last_alert = self.last_alert_time.get(error_code)
        
        # Alert thresholds: 10 errors in first occurrence, then every 100 errors
        should_alert = (
            (count == 10) or 
            (count % 100 == 0 and count > 10)
        )
        
        # Don't spam alerts - at most one per hour per error code
        if should_alert and (not last_alert or (now - last_alert).seconds > 3600):
            self._send_error_alert(error_code, count)
            self.last_alert_time[error_code] = now
    
    def _send_error_alert(self, error_code: str, count: int):
        """Send error alert (placeholder for actual alerting system)"""
        alert_message = f"Error alert: {error_code} has occurred {count} times"
        self.logger.critical(
            alert_message,
            extra={
                "alert_type": "error_frequency",
                "error_code": error_code,
                "error_count": count
            }
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of error occurrences"""
        return {
            "total_error_types": len(self.error_counts),
            "errors": dict(self.error_counts)
        }


def setup_logging():
    """Configure comprehensive application logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Determine log format based on environment
    use_json_format = settings.LOG_LEVEL.upper() == "DEBUG" or getattr(settings, 'LOG_FORMAT', 'plain') == 'json'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    if use_json_format:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(PlainFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler for general logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    if use_json_format:
        file_handler.setFormatter(StructuredFormatter())
    else:
        file_handler.setFormatter(PlainFormatter())
    
    root_logger.addHandler(file_handler)
    
    # Error-specific file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "performance.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(StructuredFormatter())
    
    # Create performance logger
    perf_logger = logging.getLogger("performance")
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Create and configure error logger
    error_logger = ErrorLogger()
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging system initialized",
        extra={
            "log_level": settings.LOG_LEVEL,
            "log_format": "json" if use_json_format else "plain",
            "log_directory": str(log_dir.absolute())
        }
    )
    
    return error_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_performance(
    operation: str,
    duration: float,
    request_id: Optional[str] = None,
    document_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Log performance metrics"""
    perf_logger = logging.getLogger("performance")
    
    extra_data = {
        "operation": operation,
        "duration_seconds": duration,
        "details": details or {}
    }
    
    if request_id:
        extra_data["request_id"] = request_id
    
    if document_id:
        extra_data["document_id"] = document_id
    
    perf_logger.info(
        f"Performance: {operation} completed in {duration:.3f}s",
        extra=extra_data
    )


def log_api_call(
    method: str,
    path: str,
    status_code: int,
    duration: float,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None
):
    """Log API call metrics"""
    api_logger = logging.getLogger("api")
    
    extra_data = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_seconds": duration,
        "request_size_bytes": request_size,
        "response_size_bytes": response_size
    }
    
    if request_id:
        extra_data["request_id"] = request_id
    
    if user_id:
        extra_data["user_id"] = user_id
    
    level = logging.INFO
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    
    api_logger.log(
        level,
        f"API {method} {path} -> {status_code} ({duration:.3f}s)",
        extra=extra_data
    )


# Global error logger instance
_error_logger = None


def get_error_logger() -> ErrorLogger:
    """Get the global error logger instance"""
    global _error_logger
    if _error_logger is None:
        _error_logger = ErrorLogger()
    return _error_logger