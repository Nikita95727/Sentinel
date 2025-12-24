"""
Enhanced error handling and logging system with full context tracking.
Provides error codes, categories, and causal chain tracking for diagnostics.
"""

import traceback
import sys
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
import uuid


class ErrorCategory(Enum):
    """Error categories for classification."""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    EXCHANGE_ERROR = "exchange_error"
    AI_ERROR = "ai_error"
    VALIDATION_ERROR = "validation_error"
    CONFIG_ERROR = "config_error"
    DATA_ERROR = "data_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    SYSTEM_ERROR = "system_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCode:
    """Error codes for different error types."""
    
    # API Errors (1000-1999)
    API_RATE_LIMIT = "API_1001"
    API_TIMEOUT = "API_1002"
    API_AUTH_FAILED = "API_1003"
    API_INVALID_RESPONSE = "API_1004"
    API_SERVER_ERROR = "API_1005"
    
    # Exchange Errors (2000-2999)
    EXCHANGE_CONNECTION_FAILED = "EXCH_2001"
    EXCHANGE_INSUFFICIENT_BALANCE = "EXCH_2002"
    EXCHANGE_INVALID_SYMBOL = "EXCH_2003"
    EXCHANGE_ORDER_REJECTED = "EXCH_2004"
    EXCHANGE_MARKET_DATA_ERROR = "EXCH_2005"
    
    # AI Errors (3000-3999)
    AI_PARSE_ERROR = "AI_3001"
    AI_VALIDATION_FAILED = "AI_3002"
    AI_TIMEOUT = "AI_3003"
    AI_INVALID_DECISION = "AI_3004"
    AI_FALLBACK_USED = "AI_3005"
    
    # Validation Errors (4000-4999)
    VALID_INVALID_PRICE = "VAL_4001"
    VALID_INVALID_SIZE = "VAL_4002"
    VALID_BLACKLISTED_SYMBOL = "VAL_4003"
    VALID_INSUFFICIENT_FUNDS = "VAL_4004"
    
    # Data Errors (5000-5999)
    DATA_LOAD_FAILED = "DATA_5001"
    DATA_SAVE_FAILED = "DATA_5002"
    DATA_CORRUPTED = "DATA_5003"
    DATA_INSUFFICIENT = "DATA_5004"
    
    # Business Logic Errors (6000-6999)
    BUSINESS_LOGIC_ERROR = "BL_6001"
    
    # System Errors (7000-7999)
    SYS_CONFIG_ERROR = "SYS_7001"
    SYS_INIT_FAILED = "SYS_7002"
    SYS_RESOURCE_EXHAUSTED = "SYS_7003"


class ErrorContext:
    """Context information for error tracking."""
    
    def __init__(
        self,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        component: str,
        symbol: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        stack_trace: Optional[str] = None
    ):
        self.error_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.utcnow().isoformat()
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.message = message
        self.component = component
        self.symbol = symbol
        self.operation = operation
        self.metadata = metadata or {}
        self.cause = cause
        self.stack_trace = stack_trace
        self.causal_chain: List[str] = []
    
    def add_cause(self, cause_id: str):
        """Add a cause to the causal chain."""
        self.causal_chain.append(cause_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'error_id': self.error_id,
            'timestamp': self.timestamp,
            'error_code': self.error_code,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'component': self.component,
            'symbol': self.symbol,
            'operation': self.operation,
            'metadata': self.metadata,
            'cause_type': type(self.cause).__name__ if self.cause else None,
            'cause_message': str(self.cause) if self.cause else None,
            'stack_trace': self.stack_trace,
            'causal_chain': self.causal_chain
        }


class ErrorHandler:
    """Enhanced error handler with context tracking."""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.max_history = 1000
    
    def handle_error(
        self,
        error: Exception,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        component: str,
        symbol: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        log_level: str = "error"
    ) -> ErrorContext:
        """
        Handle an error with full context.
        
        Args:
            error: The exception that occurred
            error_code: Error code from ErrorCode
            category: Error category
            severity: Error severity
            component: Component where error occurred
            symbol: Trading symbol (if applicable)
            operation: Operation being performed
            metadata: Additional context
            log_level: Log level (error, warning, critical)
            
        Returns:
            ErrorContext object
        """
        # Get stack trace
        stack_trace = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))
        
        # Create error context
        context = ErrorContext(
            error_code=error_code,
            category=category,
            severity=severity,
            message=str(error),
            component=component,
            symbol=symbol,
            operation=operation,
            metadata=metadata or {},
            cause=error,
            stack_trace=stack_trace
        )
        
        # Add to history
        self.error_history.append(context)
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # Log with structured format
        log_message = self._format_log_message(context)
        
        if log_level == "critical":
            logger.critical(log_message)
        elif log_level == "warning":
            logger.warning(log_message)
        else:
            logger.error(log_message)
        
        # Log full context as JSON for parsing
        logger.debug(f"ERROR_CONTEXT: {context.to_dict()}")
        
        return context
    
    def _format_log_message(self, context: ErrorContext) -> str:
        """Format error message with full context."""
        parts = [
            f"[{context.error_code}]",
            f"{context.category.value.upper()}",
            f"in {context.component}"
        ]
        
        if context.operation:
            parts.append(f"during {context.operation}")
        
        if context.symbol:
            parts.append(f"for {context.symbol}")
        
        parts.append(f": {context.message}")
        
        if context.metadata:
            metadata_str = ", ".join([f"{k}={v}" for k, v in context.metadata.items()])
            parts.append(f"({metadata_str})")
        
        return " | ".join(parts)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.error_history:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {},
                'by_component': {},
                'recent_errors': []
            }
        
        stats = {
            'total_errors': len(self.error_history),
            'by_category': {},
            'by_severity': {},
            'by_component': {},
            'recent_errors': [e.to_dict() for e in self.error_history[-10:]]
        }
        
        for error in self.error_history:
            # Count by category
            cat = error.category.value
            stats['by_category'][cat] = stats['by_category'].get(cat, 0) + 1
            
            # Count by severity
            sev = error.severity.value
            stats['by_severity'][sev] = stats['by_severity'].get(sev, 0) + 1
            
            # Count by component
            comp = error.component
            stats['by_component'][comp] = stats['by_component'].get(comp, 0) + 1
        
        return stats


# Global error handler instance
error_handler = ErrorHandler()


def log_error_with_context(
    error: Exception,
    error_code: str,
    category: ErrorCategory,
    severity: ErrorSeverity,
    component: str,
    symbol: Optional[str] = None,
    operation: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_level: str = "error"
) -> ErrorContext:
    """
    Convenience function to log error with full context.
    
    Usage:
        try:
            # some operation
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.API_TIMEOUT, ErrorCategory.API_ERROR,
                ErrorSeverity.HIGH, "GrokProvider", symbol="BTC/USDT",
                operation="analyze", metadata={"retry_count": 3}
            )
    """
    return error_handler.handle_error(
        error=error,
        error_code=error_code,
        category=category,
        severity=severity,
        component=component,
        symbol=symbol,
        operation=operation,
        metadata=metadata,
        log_level=log_level
    )

