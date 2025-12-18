"""
Rate limiting middleware for API protection
"""
import time
import logging
from typing import Dict, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from collections import defaultdict, deque


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window
    """
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps for each client
        self.minute_windows: Dict[str, deque] = defaultdict(deque)
        self.hour_windows: Dict[str, deque] = defaultdict(deque)
        
        # Last cleanup time
        self.last_cleanup = time.time()
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory leaks"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes
        if current_time - self.last_cleanup < 300:
            return
        
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        
        # Clean minute windows
        for client_id in list(self.minute_windows.keys()):
            window = self.minute_windows[client_id]
            while window and window[0] < cutoff_minute:
                window.popleft()
            if not window:
                del self.minute_windows[client_id]
        
        # Clean hour windows
        for client_id in list(self.hour_windows.keys()):
            window = self.hour_windows[client_id]
            while window and window[0] < cutoff_hour:
                window.popleft()
            if not window:
                del self.hour_windows[client_id]
        
        self.last_cleanup = current_time
    
    def is_allowed(self, client_id: str) -> tuple[bool, Optional[str], Optional[int]]:
        """
        Check if request is allowed for client
        
        Args:
            client_id: Unique identifier for client (IP address or API key)
            
        Returns:
            Tuple of (is_allowed, error_message, retry_after_seconds)
        """
        current_time = time.time()
        
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Check minute window
        minute_window = self.minute_windows[client_id]
        cutoff_minute = current_time - 60
        
        # Remove old entries from minute window
        while minute_window and minute_window[0] < cutoff_minute:
            minute_window.popleft()
        
        if len(minute_window) >= self.requests_per_minute:
            retry_after = int(60 - (current_time - minute_window[0]))
            return False, f"Rate limit exceeded: {self.requests_per_minute} requests per minute", retry_after
        
        # Check hour window
        hour_window = self.hour_windows[client_id]
        cutoff_hour = current_time - 3600
        
        # Remove old entries from hour window
        while hour_window and hour_window[0] < cutoff_hour:
            hour_window.popleft()
        
        if len(hour_window) >= self.requests_per_hour:
            retry_after = int(3600 - (current_time - hour_window[0]))
            return False, f"Rate limit exceeded: {self.requests_per_hour} requests per hour", retry_after
        
        # Add current request to windows
        minute_window.append(current_time)
        hour_window.append(current_time)
        
        return True, None, None


# Global rate limiter instance (will be initialized with settings)
rate_limiter = None


async def rate_limiting_middleware(request: Request, call_next):
    """
    Rate limiting middleware
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response or rate limit error
    """
    global rate_limiter
    
    # Initialize rate limiter with settings if not already done
    if rate_limiter is None:
        from app.core.config import settings
        rate_limiter = RateLimiter(
            requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            requests_per_hour=settings.RATE_LIMIT_REQUESTS_PER_HOUR
        )
    # Get client identifier (prefer API key, fallback to IP)
    client_id = request.headers.get("X-API-Key")
    if not client_id:
        # Use IP address as fallback
        client_ip = request.client.host if request.client else "unknown"
        # Include forwarded IP if behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        client_id = f"ip:{client_ip}"
    else:
        # Hash API key for privacy
        import hashlib
        client_id = f"key:{hashlib.sha256(client_id.encode()).hexdigest()[:16]}"
    
    # Check rate limit
    is_allowed, error_message, retry_after = rate_limiter.is_allowed(client_id)
    
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for client {client_id}: {error_message}")
        
        headers = {}
        if retry_after:
            headers["Retry-After"] = str(retry_after)
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": error_message,
                    "retry_after_seconds": retry_after,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            },
            headers=headers
        )
    
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers to response
    minute_window = rate_limiter.minute_windows.get(client_id, deque())
    hour_window = rate_limiter.hour_windows.get(client_id, deque())
    
    response.headers["X-RateLimit-Limit-Minute"] = str(rate_limiter.requests_per_minute)
    response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, rate_limiter.requests_per_minute - len(minute_window)))
    response.headers["X-RateLimit-Limit-Hour"] = str(rate_limiter.requests_per_hour)
    response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, rate_limiter.requests_per_hour - len(hour_window)))
    
    return response