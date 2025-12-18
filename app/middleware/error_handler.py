"""
Global error handling middleware for the Contract OCR API
"""
import logging
import traceback
import uuid
from typing import Union, Dict, Any
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.core.errors import (
    APIError, ErrorCode, ErrorCategory, InternalError, ValidationError,
    get_http_status_for_error_code
)
from app.core.logging import get_error_logger, get_logger


logger = get_logger(__name__)
error_logger = get_error_logger()


async def global_exception_handler(request: Request, call_next):
    """
    Global exception handling middleware
    
    Catches all unhandled exceptions and converts them to structured error responses
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4()))
    
    try:
        response = await call_next(request)
        return response
        
    except APIError as e:
        # Handle our custom API errors
        return await handle_api_error(e, request_id)
        
    except HTTPException as e:
        # Handle FastAPI HTTP exceptions
        return await handle_http_exception(e, request_id)
        
    except StarletteHTTPException as e:
        # Handle Starlette HTTP exceptions
        return await handle_starlette_exception(e, request_id)
        
    except RequestValidationError as e:
        # Handle Pydantic validation errors
        return await handle_validation_error(e, request_id)
        
    except SQLAlchemyError as e:
        # Handle database errors
        return await handle_database_error(e, request_id)
        
    except Exception as e:
        # Handle all other unexpected exceptions
        return await handle_unexpected_error(e, request_id)


async def handle_api_error(error: APIError, request_id: str) -> JSONResponse:
    """Handle custom API errors"""
    
    # Log the error
    error_logger.log_error(
        error_code=error.code.value,
        message=error.message,
        category=error.category.value,
        request_id=request_id,
        details=error.details
    )
    
    # Create response
    error_data = error.to_dict()
    error_data["error"]["request_id"] = request_id
    
    headers = {}
    if error.retry_after:
        headers["Retry-After"] = str(error.retry_after)
    
    return JSONResponse(
        status_code=error.status_code,
        content=error_data,
        headers=headers
    )


async def handle_http_exception(error: HTTPException, request_id: str) -> JSONResponse:
    """Handle FastAPI HTTP exceptions"""
    
    # Map to our error system
    if error.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = ErrorCode.INVALID_API_KEY
        category = ErrorCategory.AUTHENTICATION
    elif error.status_code == status.HTTP_403_FORBIDDEN:
        error_code = ErrorCode.ACCESS_DENIED
        category = ErrorCategory.AUTHORIZATION
    elif error.status_code == status.HTTP_404_NOT_FOUND:
        error_code = ErrorCode.RESOURCE_NOT_FOUND
        category = ErrorCategory.NOT_FOUND
    elif error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        error_code = ErrorCode.INVALID_PARAMETER
        category = ErrorCategory.VALIDATION
    elif error.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        error_code = ErrorCode.RATE_LIMIT_EXCEEDED
        category = ErrorCategory.RATE_LIMIT
    else:
        error_code = ErrorCode.INTERNAL_SERVER_ERROR
        category = ErrorCategory.INTERNAL
    
    # Extract details from HTTPException
    details = {}
    if hasattr(error, 'detail') and isinstance(error.detail, dict):
        details = error.detail
    elif hasattr(error, 'detail'):
        details = {"detail": str(error.detail)}
    
    # Log the error
    error_logger.log_error(
        error_code=error_code.value,
        message=str(error.detail) if hasattr(error, 'detail') else "HTTP Exception",
        category=category.value,
        request_id=request_id,
        details=details
    )
    
    # Create structured response
    error_data = {
        "error": {
            "code": error_code.value,
            "message": str(error.detail) if hasattr(error, 'detail') else "HTTP Exception",
            "category": category.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    return JSONResponse(
        status_code=error.status_code,
        content=error_data
    )


async def handle_starlette_exception(error: StarletteHTTPException, request_id: str) -> JSONResponse:
    """Handle Starlette HTTP exceptions"""
    
    # Map to our error system
    if error.status_code == status.HTTP_404_NOT_FOUND:
        error_code = ErrorCode.ENDPOINT_NOT_FOUND
        category = ErrorCategory.NOT_FOUND
        message = "Endpoint not found"
    else:
        error_code = ErrorCode.INTERNAL_SERVER_ERROR
        category = ErrorCategory.INTERNAL
        message = str(error.detail) if hasattr(error, 'detail') else "Internal server error"
    
    # Log the error
    error_logger.log_error(
        error_code=error_code.value,
        message=message,
        category=category.value,
        request_id=request_id
    )
    
    # Create structured response
    error_data = {
        "error": {
            "code": error_code.value,
            "message": message,
            "category": category.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    }
    
    return JSONResponse(
        status_code=error.status_code,
        content=error_data
    )


async def handle_validation_error(error: RequestValidationError, request_id: str) -> JSONResponse:
    """Handle Pydantic validation errors"""
    
    # Extract validation details
    validation_details = []
    for err in error.errors():
        validation_details.append({
            "field": ".".join(str(x) for x in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
            "input": err.get("input")
        })
    
    details = {
        "validation_errors": validation_details,
        "error_count": len(validation_details)
    }
    
    # Log the error
    error_logger.log_error(
        error_code=ErrorCode.INVALID_PARAMETER.value,
        message=f"Request validation failed: {len(validation_details)} errors",
        category=ErrorCategory.VALIDATION.value,
        request_id=request_id,
        details=details
    )
    
    # Create structured response
    error_data = {
        "error": {
            "code": ErrorCode.INVALID_PARAMETER.value,
            "message": "Request validation failed",
            "category": ErrorCategory.VALIDATION.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id,
            "details": details
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_data
    )


async def handle_database_error(error: SQLAlchemyError, request_id: str) -> JSONResponse:
    """Handle database errors"""
    
    # Log the full error for debugging
    logger.error(
        f"Database error: {str(error)}",
        extra={
            "request_id": request_id,
            "error_type": type(error).__name__
        },
        exc_info=True
    )
    
    # Log structured error
    error_logger.log_error(
        error_code=ErrorCode.DATABASE_ERROR.value,
        message="Database operation failed",
        category=ErrorCategory.STORAGE.value,
        request_id=request_id,
        details={
            "error_type": type(error).__name__,
            "error_message": str(error)
        },
        exc_info=(type(error), error, error.__traceback__)
    )
    
    # Create user-friendly response (don't expose internal details)
    error_data = {
        "error": {
            "code": ErrorCode.DATABASE_ERROR.value,
            "message": "A database error occurred. Please try again later.",
            "category": ErrorCategory.STORAGE.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_data
    )


async def handle_unexpected_error(error: Exception, request_id: str) -> JSONResponse:
    """Handle unexpected errors"""
    
    # Log the full error for debugging
    logger.error(
        f"Unexpected error: {str(error)}",
        extra={
            "request_id": request_id,
            "error_type": type(error).__name__
        },
        exc_info=True
    )
    
    # Log structured error
    error_logger.log_error(
        error_code=ErrorCode.UNEXPECTED_ERROR.value,
        message=f"Unexpected error: {type(error).__name__}",
        category=ErrorCategory.INTERNAL.value,
        request_id=request_id,
        details={
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc()
        },
        exc_info=(type(error), error, error.__traceback__)
    )
    
    # Create user-friendly response (don't expose internal details)
    error_data = {
        "error": {
            "code": ErrorCode.UNEXPECTED_ERROR.value,
            "message": "An unexpected error occurred. Please try again later.",
            "category": ErrorCategory.INTERNAL.value,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_data
    )


def create_error_response(
    code: ErrorCode,
    message: str,
    status_code: int = None,
    details: Dict[str, Any] = None,
    request_id: str = None,
    retry_after: int = None
) -> JSONResponse:
    """
    Create a standardized error response
    
    Args:
        code: Error code
        message: Error message
        status_code: HTTP status code (auto-determined if not provided)
        details: Additional error details
        request_id: Request ID for tracking
        retry_after: Seconds to wait before retry (for rate limiting)
    
    Returns:
        JSONResponse with structured error format
    """
    if status_code is None:
        status_code = get_http_status_for_error_code(code)
    
    # Determine category based on error code
    if code.value.startswith(('INVALID_', 'MISSING_', 'EMPTY_', 'UNSAFE_')):
        category = ErrorCategory.VALIDATION
    elif code.value.startswith(('MISSING_API_KEY', 'INVALID_API_KEY', 'EXPIRED_API_KEY')):
        category = ErrorCategory.AUTHENTICATION
    elif code.value.startswith(('INSUFFICIENT_', 'ACCESS_DENIED')):
        category = ErrorCategory.AUTHORIZATION
    elif code.value.endswith('_NOT_FOUND'):
        category = ErrorCategory.NOT_FOUND
    elif code.value.endswith(('_PROCESSING_ERROR', '_NOT_COMPLETED')):
        category = ErrorCategory.PROCESSING
    elif code.value.startswith('RATE_LIMIT_'):
        category = ErrorCategory.RATE_LIMIT
    elif code.value.endswith(('_STORAGE_ERROR', '_DATABASE_ERROR')):
        category = ErrorCategory.STORAGE
    elif code.value.endswith(('_SERVICE_', '_UNAVAILABLE')):
        category = ErrorCategory.EXTERNAL_SERVICE
    else:
        category = ErrorCategory.INTERNAL
    
    error_data = {
        "error": {
            "code": code.value,
            "message": message,
            "category": category.value,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    if details:
        error_data["error"]["details"] = details
    
    if request_id:
        error_data["error"]["request_id"] = request_id
    
    if retry_after:
        error_data["error"]["retry_after"] = retry_after
    
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    
    return JSONResponse(
        status_code=status_code,
        content=error_data,
        headers=headers
    )