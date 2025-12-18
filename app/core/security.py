"""
Security utilities for authentication and authorization
"""
import os
import secrets
import hashlib
from typing import Optional, List
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.core.config import settings


# API Key header security scheme
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


def get_valid_api_keys() -> List[str]:
    """
    Get list of valid API keys from environment
    
    Returns:
        List of valid API key hashes
    """
    # Get API keys from environment (comma-separated)
    api_keys_str = os.getenv("API_KEYS", "")
    
    if not api_keys_str:
        # If no API keys configured, generate a default one for development
        if not settings.REQUIRE_API_KEY:
            return []
        
        # In production, this should fail if no keys are configured
        default_key = os.getenv("DEFAULT_API_KEY", "dev-key-12345")
        return [hash_api_key(default_key)]
    
    # Split and hash the keys
    keys = [key.strip() for key in api_keys_str.split(",") if key.strip()]
    return [hash_api_key(key) for key in keys]


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage and comparison
    
    Args:
        api_key: Raw API key string
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    """
    Generate a secure random API key
    
    Returns:
        New API key string
    """
    return secrets.token_urlsafe(32)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify API key from request header
    
    Args:
        api_key: API key from request header
        
    Returns:
        Validated API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # If API key authentication is not required, skip validation
    if not settings.REQUIRE_API_KEY:
        return "anonymous"
    
    # Check if API key is provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "MISSING_API_KEY",
                    "message": f"API key is required. Please provide it in the '{settings.API_KEY_HEADER}' header.",
                }
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Get valid API keys
    valid_keys = get_valid_api_keys()
    
    # Hash the provided key and check against valid keys
    hashed_key = hash_api_key(api_key)
    
    if hashed_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_API_KEY",
                    "message": "Invalid API key provided.",
                }
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key
