"""
Enhanced logging configuration with structured output and context tracking.
"""

import sys
import json
from typing import Dict, Any
from loguru import logger
from datetime import datetime


class StructuredLogger:
    """Structured logger with context tracking."""
    
    def __init__(self):
        self.context: Dict[str, Any] = {}
    
    def add_context(self, key: str, value: Any):
        """Add context to all subsequent log messages."""
        self.context[key] = value
    
    def clear_context(self):
        """Clear all context."""
        self.context.clear()
    
    def _format_record(self, record: Dict[str, Any]) -> str:
        """Format log record with context."""
        # Base log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record['level'].name,
            'message': record['message'],
            'module': record['name'],
            'function': record['function'],
            'line': record['line']
        }
        
        # Add context if available
        if self.context:
            log_data['context'] = self.context.copy()
        
        # Add exception info if present
        if record.get('exception'):
            log_data['exception'] = {
                'type': record['exception'].type.__name__,
                'message': str(record['exception'].value),
                'traceback': record['exception'].traceback
            }
        
        return json.dumps(log_data, default=str)
    
    def info(self, message: str, **kwargs):
        """Log info message with context."""
        logger.bind(**self.context).info(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with context."""
        logger.bind(**self.context).error(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with context."""
        logger.bind(**self.context).warning(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with context."""
        logger.bind(**self.context).debug(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with context."""
        logger.bind(**self.context).critical(message, **kwargs)


def setup_enhanced_logging(
    log_level: str = "INFO",
    log_file: str = "logs/sentinel_{time:YYYY-MM-DD}.log",
    json_log_file: Optional[str] = "logs/sentinel_{time:YYYY-MM-DD}.jsonl",
    enable_json: bool = True
):
    """
    Setup enhanced logging with structured output.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file with rotation
        json_log_file: Path to JSON log file (optional)
        enable_json: Enable JSON structured logging
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # File handler with rotation
    logger.add(
        log_file,
        rotation="00:00",  # Rotate at midnight
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    # JSON structured logging (optional)
    if enable_json and json_log_file:
        def json_sink(message):
            """JSON log sink."""
            record = message.record
            log_entry = {
                'timestamp': record['time'].isoformat(),
                'level': record['level'].name,
                'message': record['message'],
                'module': record['name'],
                'function': record['function'],
                'line': record['line'],
                'process': record['process'].id,
                'thread': record['thread'].id
            }
            
            # Add exception info if present
            if record.get('exception'):
                log_entry['exception'] = {
                    'type': record['exception'].type.__name__,
                    'message': str(record['exception'].value)
                }
            
            # Write to JSONL file
            with open(json_log_file.format(time=record['time']), 'a') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
        
        logger.add(json_sink, level=log_level, format="{message}")
    
    logger.info("Enhanced logging configured", level=log_level)


# Global structured logger instance
structured_logger = StructuredLogger()

