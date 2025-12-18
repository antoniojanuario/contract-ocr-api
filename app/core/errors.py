"""
Comprehensive error handling and categorization for the Contract OCR API
"""
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from fastapi import status
from pydantic import BaseModel


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    PROCESSING = "processing"
    STORAGE = "storage"
    EXTERNAL_SERVICE = "external_service"
    RATE_LIMIT = "rate_limit"
    INTERNAL = "internal"


class ErrorCode(str, Enum):
    """Standardized error codes"""
    # Validation errors (400)
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    EMPTY_FILE = "EMPTY_FILE"
    MISSING_FILENAME = "MISSING_FILENAME"
    INVALID_FILE_EXTENSION = "INVALID_FILE_EXTENSION"
    UNSAFE_FILENAME = "UNSAFE_FILENAME"
    PDF_VALIDATION_ERROR = "PDF_VALIDATION_ERROR"
    INVALID_DOCUMENT_ID = "INVALID_DOCUMENT_ID"
    INVALID_STATUS_FILTER = "INVALID_STATUS_FILTER"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    
    # Authentication errors (401)
    MISSING_API_KEY = "MISSING_API_KEY"
    INVALID_API_KEY = "INVALID_API_KEY"
    EXPIRED_API_KEY = "EXPIRED_API_KEY"
    
    # Authorization errors (403)
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ACCESS_DENIED = "ACCESS_DENIED"
    
    # Not found errors (404)
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"
    
    # Processing errors (422)
    PROCESSING_NOT_COMPLETED = "PROCESSING_NOT_COMPLETED"
    OCR_PROCESSING_ERROR = "OCR_PROCESSING_ERROR"
    TEXT_NORMALIZATION_ERROR = "TEXT_NORMALIZATION_ERROR"
    PAGE_EXTRACTION_ERROR = "PAGE_EXTRACTION_ERROR"
    
    # Rate limiting errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUEUE_CAPACITY_EXCEEDED = "QUEUE_CAPACITY_EXCEEDED"
    
    # Storage errors (500)
    FILE_STORAGE_ERROR = "FILE_STORAGE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    
    # External service errors (502/503)
    OCR_SERVICE_UNAVAILABLE = "OCR_SERVICE_UNAVAILABLE"
    WEBHOOK_DELIVERY_FAILED = "WEBHOOK_DELIVERY_FAILED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    
    # Internal errors (500)
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    
    # Upload errors
    UPLOAD_ERROR = "UPLOAD_ERROR"
    
    # Webhook errors
    MISSING_WEBHOOK_URL = "MISSING_WEBHOOK_URL"
    INVALID_WEBHOOK_URL = "INVALID_WEBHOOK_URL"
    WEBHOOK_CONFIGURATION_FAILED = "WEBHOOK_CONFIGURATION_FAILED"


class ErrorDetail(BaseModel):
    """Structured error detail"""
    code: ErrorCode
    message: str
    category: ErrorCategory
    details: Optional[Dict[str, Any]] = None
    timestamp: str
    request_id: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    
    class Config:
        use_enum_values = True


class APIError(Exception):
    """Base exception for API errors"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        category: ErrorCategory,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        self.code = code
        self.message = message
        self.category = category
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id
        self.retry_after = retry_after
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        error_data = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "category": self.category.value,
                "timestamp": self.timestamp
            }
        }
        
        if self.details:
            error_data["error"]["details"] = self.details
        
        if self.request_id:
            error_data["error"]["request_id"] = self.request_id
        
        if self.retry_after:
            error_data["error"]["retry_after"] = self.retry_after
        
        return error_data


# Specific error classes for different categories

class ValidationError(APIError):
    """Validation error (400)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.VALIDATION,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            request_id=request_id
        )


class AuthenticationError(APIError):
    """Authentication error (401)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            request_id=request_id
        )


class AuthorizationError(APIError):
    """Authorization error (403)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.AUTHORIZATION,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            request_id=request_id
        )


class NotFoundError(APIError):
    """Not found error (404)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            request_id=request_id
        )


class ProcessingError(APIError):
    """Processing error (422)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.PROCESSING,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            request_id=request_id
        )


class RateLimitError(APIError):
    """Rate limit error (429)"""
    def __init__(self, code: ErrorCode, message: str, retry_after: int = 60, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.RATE_LIMIT,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            request_id=request_id,
            retry_after=retry_after
        )


class StorageError(APIError):
    """Storage error (500)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.STORAGE,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            request_id=request_id
        )


class ExternalServiceError(APIError):
    """External service error (502/503)"""
    def __init__(self, code: ErrorCode, message: str, retry_after: Optional[int] = None, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.EXTERNAL_SERVICE,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            request_id=request_id,
            retry_after=retry_after
        )


class InternalError(APIError):
    """Internal server error (500)"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
        super().__init__(
            code=code,
            message=message,
            category=ErrorCategory.INTERNAL,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            request_id=request_id
        )


# Error mapping for HTTP status codes
ERROR_CODE_TO_HTTP_STATUS = {
    # Validation errors
    ErrorCode.INVALID_FILE_FORMAT: status.HTTP_400_BAD_REQUEST,
    ErrorCode.FILE_TOO_LARGE: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    ErrorCode.EMPTY_FILE: status.HTTP_400_BAD_REQUEST,
    ErrorCode.MISSING_FILENAME: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_FILE_EXTENSION: status.HTTP_400_BAD_REQUEST,
    ErrorCode.UNSAFE_FILENAME: status.HTTP_400_BAD_REQUEST,
    ErrorCode.PDF_VALIDATION_ERROR: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_DOCUMENT_ID: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_STATUS_FILTER: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_PARAMETER: status.HTTP_400_BAD_REQUEST,
    ErrorCode.MISSING_REQUIRED_FIELD: status.HTTP_400_BAD_REQUEST,
    
    # Authentication errors
    ErrorCode.MISSING_API_KEY: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.INVALID_API_KEY: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.EXPIRED_API_KEY: status.HTTP_401_UNAUTHORIZED,
    
    # Authorization errors
    ErrorCode.INSUFFICIENT_PERMISSIONS: status.HTTP_403_FORBIDDEN,
    ErrorCode.ACCESS_DENIED: status.HTTP_403_FORBIDDEN,
    
    # Not found errors
    ErrorCode.DOCUMENT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorCode.ENDPOINT_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    
    # Processing errors
    ErrorCode.PROCESSING_NOT_COMPLETED: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.OCR_PROCESSING_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.TEXT_NORMALIZATION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ErrorCode.PAGE_EXTRACTION_ERROR: status.HTTP_422_UNPROCESSABLE_ENTITY,
    
    # Rate limiting errors
    ErrorCode.RATE_LIMIT_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.QUEUE_CAPACITY_EXCEEDED: status.HTTP_429_TOO_MANY_REQUESTS,
    
    # Storage errors
    ErrorCode.FILE_STORAGE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.DATABASE_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # External service errors
    ErrorCode.OCR_SERVICE_UNAVAILABLE: status.HTTP_503_SERVICE_UNAVAILABLE,
    ErrorCode.WEBHOOK_DELIVERY_FAILED: status.HTTP_502_BAD_GATEWAY,
    ErrorCode.EXTERNAL_SERVICE_ERROR: status.HTTP_503_SERVICE_UNAVAILABLE,
    
    # Internal errors
    ErrorCode.INTERNAL_SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.CONFIGURATION_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.UNEXPECTED_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.UPLOAD_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
    
    # Webhook errors
    ErrorCode.MISSING_WEBHOOK_URL: status.HTTP_400_BAD_REQUEST,
    ErrorCode.INVALID_WEBHOOK_URL: status.HTTP_400_BAD_REQUEST,
    ErrorCode.WEBHOOK_CONFIGURATION_FAILED: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def get_http_status_for_error_code(error_code: ErrorCode) -> int:
    """Get HTTP status code for an error code"""
    return ERROR_CODE_TO_HTTP_STATUS.get(error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
