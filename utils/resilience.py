"""
Resilience utilities for API error handling.
Includes retry logic, circuit breaker, and rate limit handling.
"""

import asyncio
import functools
from datetime import datetime, timedelta
from typing import Callable, Any, Optional
from loguru import logger


class CircuitBreaker:
    """
    Circuit breaker pattern to protect against cascading failures.
    
    States:
    - closed: Normal operation
    - open: Blocking requests after threshold failures
    - half_open: Testing if service recovered
    """
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Time to wait before trying half-open
        """
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'closed'  # closed, open, half_open
        self.success_count = 0  # For half-open state
        
    def call(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker to async function."""
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if circuit is open
            if self.state == 'open':
                if self.last_failure_time and \
                   datetime.now() - self.last_failure_time > self.timeout:
                    # Try half-open
                    self.state = 'half_open'
                    self.failures = 0
                    self.success_count = 0
                    logger.info("Circuit breaker: Attempting half-open state")
                else:
                    raise Exception(
                        f"Circuit breaker is OPEN. "
                        f"Last failure: {self.last_failure_time}"
                    )
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - reset failures
                if self.state == 'half_open':
                    self.success_count += 1
                    if self.success_count >= 2:  # 2 successes to close
                        self.state = 'closed'
                        logger.info("Circuit breaker: CLOSED (service recovered)")
                elif self.state == 'closed':
                    self.failures = 0
                
                return result
                
            except Exception as e:
                self.failures += 1
                self.last_failure_time = datetime.now()
                
                if self.failures >= self.failure_threshold:
                    self.state = 'open'
                    logger.warning(
                        f"⚠️ Circuit breaker OPENED after {self.failures} failures. "
                        f"Service will be blocked for {self.timeout.total_seconds()}s"
                    )
                
                raise e
        
        return wrapper
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.state = 'closed'
        self.failures = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


def retry_on_error(
    max_attempts: int = 3,
    delay_seconds: int = 5,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay_seconds: Initial delay between retries
        backoff: Backoff multiplier (2.0 = exponential)
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = delay_seconds
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Special handling for rate limits
                    error_str = str(e).lower()
                    if "rate limit" in error_str or "429" in error_str:
                        delay = 60  # Wait longer for rate limits
                        logger.warning(
                            f"Rate limit detected. Waiting {delay}s before retry"
                        )
                    
                    if attempt < max_attempts - 1:
                        logger.debug(
                            f"🔄 Retry {attempt + 1}/{max_attempts} for "
                            f"{func.__name__} after {delay}s: {e}"
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            f"❌ All {max_attempts} attempts failed for "
                            f"{func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


# Global circuit breaker instances for reuse
exchange_circuit = CircuitBreaker(failure_threshold=5, timeout_seconds=60)
ai_circuit = CircuitBreaker(failure_threshold=3, timeout_seconds=120)

