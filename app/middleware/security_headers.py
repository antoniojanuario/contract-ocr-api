"""
Security headers middleware for enhanced security
"""
from fastapi import Request, Response


async def security_headers_middleware(request: Request, call_next):
    """
    Add security headers to all responses
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response with security headers added
    """
    response = await call_next(request)
    
    # Check if this is a documentation endpoint
    is_docs_endpoint = request.url.path in ["/docs", "/redoc"] or request.url.path.startswith("/docs/")
    
    # Base security headers
    security_headers = {
        # Prevent MIME type sniffing
        "X-Content-Type-Options": "nosniff",
        
        # Enable XSS protection
        "X-XSS-Protection": "1; mode=block",
        
        # Referrer policy
        "Referrer-Policy": "strict-origin-when-cross-origin",
        
        # Permissions policy (formerly Feature Policy)
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        
        # Server identification
        "Server": "Contract-OCR-API/1.0",
    }
    
    # Adjust headers for documentation endpoints
    if is_docs_endpoint:
        # More permissive CSP for Swagger UI
        security_headers.update({
            "X-Frame-Options": "SAMEORIGIN",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net https://unpkg.com; connect-src 'self' http://127.0.0.1:8000 http://localhost:8000;",
            "Cache-Control": "public, max-age=3600",  # Allow caching for docs
        })
    else:
        # Stricter headers for API endpoints
        security_headers.update({
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    
    # Add HSTS header for HTTPS connections
    if request.url.scheme == "https":
        security_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Apply headers to response
    for header, value in security_headers.items():
        response.headers[header] = value
    
    return response