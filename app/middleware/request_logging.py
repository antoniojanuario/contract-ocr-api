"""
Request logging middleware for monitoring and debugging
"""
import time
import uuid
import logging
from typing import Optional
from fastapi import Request, Response
from datetime import datetime


logger = logging.getLogger(__name__)


async def request_logging_middleware(request: Request, call_next):
    """
    Log all incoming requests and responses
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response with request logging
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Add request ID to request state for use in endpoints
    request.state.request_id = request_id
    
    # Start timing
    start_time = time.time()
    
    # Get client information
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    user_agent = request.headers.get("User-Agent", "unknown")
    
    # Get API key info (without logging the actual key)
    api_key_provided = bool(request.headers.get("X-API-Key"))
    
    # Log request
    logger.info(
        f"Request started - ID: {request_id} | "
        f"Method: {request.method} | "
        f"Path: {request.url.path} | "
        f"Query: {request.url.query} | "
        f"Client: {client_ip} | "
        f"User-Agent: {user_agent} | "
        f"API-Key-Provided: {api_key_provided}"
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Request completed - ID: {request_id} | "
            f"Status: {response.status_code} | "
            f"Duration: {process_time:.3f}s"
        )
        
        # Add request ID and timing to response headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        
        return response
        
    except Exception as e:
        # Calculate processing time for failed requests
        process_time = time.time() - start_time
        
        # Log error
        logger.error(
            f"Request failed - ID: {request_id} | "
            f"Duration: {process_time:.3f}s | "
            f"Error: {str(e)}"
        )
        
        # Re-raise the exception
        raise


def get_request_id(request: Request) -> Optional[str]:
    """
    Get request ID from request state
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request ID if available
    """
    return getattr(request.state, "request_id", None)