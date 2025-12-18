"""
Retry mechanisms and graceful degradation utilities
"""
import asyncio
import logging
import time
from typing import Callable, Any, Optional, Union, Type, Tuple
from functools import wraps
from datetime import datetime, timedelta

from app.core.errors import ExternalServiceError, ErrorCode
from app.core.logging import get_logger, log_performance


logger = get_logger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        backoff_strategy: str = "exponential"  # "exponential", "linear", "fixed"
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.backoff_strategy = backoff_strategy
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number"""
        if self.backoff_strategy == "exponential":
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * attempt
        else:  # fixed
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # "closed", "open", "half-open"
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply circuit breaker"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                logger.info(f"Circuit breaker half-open for {func.__name__}")
            else:
                raise ExternalServiceError(
                    code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    message=f"Circuit breaker is open for {func.__name__}",
                    retry_after=int(self.recovery_timeout)
                )
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit breaker"""
        if self.last_failure_time is None:
            return True
        
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution"""
        if self.state == "half-open":
            self.state = "closed"
            logger.info("Circuit breaker closed after successful recovery")
        
        self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures",
                extra={"failure_count": self.failure_count}
            )


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None
):
    """
    Decorator for retrying functions with configurable backoff
    
    Args:
        config: Retry configuration
        exceptions: Tuple of exceptions to retry on
        on_retry: Callback function called on each retry attempt
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            start_time = time.time()
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    # Log successful retry if it wasn't the first attempt
                    if attempt > 1:
                        duration = time.time() - start_time
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "total_duration": duration
                            }
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Log the retry attempt
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": config.max_attempts,
                            "exception_type": type(e).__name__
                        }
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    # Don't delay after the last attempt
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        logger.debug(f"Retrying {func.__name__} in {delay:.2f} seconds")
                        await asyncio.sleep(delay)
            
            # All attempts failed
            total_duration = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {config.max_attempts} attempts",
                extra={
                    "function": func.__name__,
                    "max_attempts": config.max_attempts,
                    "total_duration": total_duration,
                    "final_exception": str(last_exception)
                }
            )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            start_time = time.time()
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log successful retry if it wasn't the first attempt
                    if attempt > 1:
                        duration = time.time() - start_time
                        logger.info(
                            f"Function {func.__name__} succeeded on attempt {attempt}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "total_duration": duration
                            }
                        )
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Log the retry attempt
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "max_attempts": config.max_attempts,
                            "exception_type": type(e).__name__
                        }
                    )
                    
                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt, e)
                    
                    # Don't delay after the last attempt
                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        logger.debug(f"Retrying {func.__name__} in {delay:.2f} seconds")
                        time.sleep(delay)
            
            # All attempts failed
            total_duration = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {config.max_attempts} attempts",
                extra={
                    "function": func.__name__,
                    "max_attempts": config.max_attempts,
                    "total_duration": total_duration,
                    "final_exception": str(last_exception)
                }
            )
            
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class GracefulDegradation:
    """Graceful degradation utilities"""
    
    @staticmethod
    def with_fallback(
        primary_func: Callable,
        fallback_func: Callable,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
        log_fallback: bool = True
    ) -> Callable:
        """
        Execute primary function with fallback on failure
        
        Args:
            primary_func: Primary function to execute
            fallback_func: Fallback function to execute on failure
            exceptions: Exceptions that trigger fallback
            log_fallback: Whether to log fallback usage
        """
        async def async_wrapper(*args, **kwargs):
            try:
                return await primary_func(*args, **kwargs)
            except exceptions as e:
                if log_fallback:
                    logger.warning(
                        f"Primary function {primary_func.__name__} failed, using fallback",
                        extra={
                            "primary_function": primary_func.__name__,
                            "fallback_function": fallback_func.__name__,
                            "exception": str(e)
                        }
                    )
                
                return await fallback_func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            try:
                return primary_func(*args, **kwargs)
            except exceptions as e:
                if log_fallback:
                    logger.warning(
                        f"Primary function {primary_func.__name__} failed, using fallback",
                        extra={
                            "primary_function": primary_func.__name__,
                            "fallback_function": fallback_func.__name__,
                            "exception": str(e)
                        }
                    )
                
                return fallback_func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(primary_func):
            return async_wrapper
        else:
            return sync_wrapper
    
    @staticmethod
    def with_timeout(
        func: Callable,
        timeout_seconds: float,
        timeout_message: str = "Operation timed out"
    ) -> Callable:
        """
        Execute function with timeout
        
        Args:
            func: Function to execute
            timeout_seconds: Timeout in seconds
            timeout_message: Message for timeout exception
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Function {func.__name__} timed out after {timeout_seconds}s",
                    extra={
                        "function": func.__name__,
                        "timeout_seconds": timeout_seconds
                    }
                )
                raise ExternalServiceError(
                    code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    message=timeout_message
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError(timeout_message)
            
            # Set up timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout_seconds))
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Cancel timeout
                return result
            except TimeoutError:
                logger.error(
                    f"Function {func.__name__} timed out after {timeout_seconds}s",
                    extra={
                        "function": func.__name__,
                        "timeout_seconds": timeout_seconds
                    }
                )
                raise ExternalServiceError(
                    code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                    message=timeout_message
                )
            finally:
                signal.signal(signal.SIGALRM, old_handler)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper


# Predefined retry configurations for common scenarios

# OCR processing retry - more attempts, longer delays
OCR_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0,
    backoff_strategy="exponential"
)

# Database operation retry - fewer attempts, shorter delays
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
    backoff_strategy="exponential"
)

# External API retry - moderate attempts and delays
API_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=1.5,
    backoff_strategy="exponential"
)

# File operation retry - quick retries
FILE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=0.1,
    max_delay=2.0,
    exponential_base=2.0,
    backoff_strategy="exponential"
)