"""
Contract OCR API - Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import api_router

# Setup logging
error_logger = setup_logging()


def _get_api_servers():
    """Get API servers configuration based on environment"""
    if settings.ENVIRONMENT == "local":
        return [
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local development server (127.0.0.1)"
            },
            {
                "url": "http://localhost:8000",
                "description": "Local development server (localhost)"
            },
            {
                "url": "https://api.contractocr.com",
                "description": "Production server"
            }
        ]
    elif settings.ENVIRONMENT == "render":
        return [
            {
                "url": "https://your-app.onrender.com",
                "description": "Render deployment"
            },
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local development server"
            }
        ]
    elif settings.ENVIRONMENT == "railway":
        return [
            {
                "url": "https://your-app.up.railway.app",
                "description": "Railway deployment"
            },
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local development server"
            }
        ]
    else:
        return [
            {
                "url": "https://api.contractocr.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.contractocr.com", 
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            }
        ]

# Create FastAPI application with comprehensive OpenAPI configuration
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
## Contract OCR API

A specialized API for extracting and normalizing text from contract documents using advanced OCR techniques.

### Key Features

* **Multi-Engine OCR**: Uses EasyOCR, PaddleOCR, and Tesseract for maximum accuracy
* **Text Normalization**: Advanced post-processing for legal document consistency
* **Page Organization**: Maintains document structure with page-level content mapping
* **Asynchronous Processing**: Queue-based processing for handling large documents
* **Copilot Studio Ready**: Optimized for Microsoft Copilot Studio integration

### Authentication

All endpoints require an API key passed in the `X-API-Key` header.

### Rate Limits

* 60 requests per minute per API key
* 1000 requests per hour per API key

### File Requirements

* **Format**: PDF only
* **Size**: Maximum 50MB
* **Pages**: Up to 100 pages per document
* **Quality**: Standard resolution recommended for best OCR results

### Processing Flow

1. **Upload** document via `/api/v1/documents/upload`
2. **Track** processing status via `/api/v1/documents/{id}/status`
3. **Retrieve** results via `/api/v1/documents/{id}/results`
4. **Optional**: Configure webhooks for completion notifications

### Integration Examples

See the `/docs` endpoint for interactive examples and Copilot Studio integration templates.
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Contract OCR API Support",
        "email": "support@contractocr.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=_get_api_servers(),
    openapi_tags=[
        {
            "name": "documents",
            "description": "Document upload, processing, and retrieval operations",
        },
        {
            "name": "monitoring",
            "description": "System health and monitoring endpoints",
        },
        {
            "name": "integration",
            "description": "Integration examples and templates for external systems",
        }
    ]
)

# Add global error handling middleware (should be first)
from app.middleware.error_handler import global_exception_handler
app.middleware("http")(global_exception_handler)

# Add security and monitoring middleware (order matters!)
if settings.ENABLE_REQUEST_LOGGING:
    from app.middleware.request_logging import request_logging_middleware
    app.middleware("http")(request_logging_middleware)

if settings.ENABLE_SECURITY_HEADERS:
    from app.middleware.security_headers import security_headers_middleware
    app.middleware("http")(security_headers_middleware)

# Add rate limiting middleware
from app.middleware.rate_limiting import rate_limiting_middleware
app.middleware("http")(rate_limiting_middleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Customize OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers
    )
    
    # Add custom examples and enhanced documentation
    openapi_schema["info"]["x-logo"] = {
        "url": "https://api.contractocr.com/static/logo.png",
        "altText": "Contract OCR API"
    }
    
    # Add comprehensive examples to the schema
    if "paths" in openapi_schema:
        # Enhance upload endpoint
        upload_path = openapi_schema["paths"].get("/api/v1/documents/upload", {})
        if "post" in upload_path:
            upload_path["post"]["x-codeSamples"] = [
                {
                    "lang": "curl",
                    "source": '''curl -X POST "https://api.contractocr.com/api/v1/documents/upload" \\
     -H "X-API-Key: your-api-key" \\
     -F "file=@contract.pdf"'''
                },
                {
                    "lang": "python",
                    "source": '''import requests

headers = {'X-API-Key': 'your-api-key'}
files = {'file': open('contract.pdf', 'rb')}

response = requests.post(
    'https://api.contractocr.com/api/v1/documents/upload',
    headers=headers,
    files=files
)

result = response.json()
print(f"Document ID: {result['document_id']}")'''
                },
                {
                    "lang": "javascript",
                    "source": '''const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('https://api.contractocr.com/api/v1/documents/upload', {
    method: 'POST',
    headers: {
        'X-API-Key': 'your-api-key'
    },
    body: formData
})
.then(response => response.json())
.then(data => console.log('Document ID:', data.document_id));'''
                }
            ]
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication. Get your key from the dashboard."
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"ApiKeyAuth": []}]
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Complete Integration Guide",
        "url": "https://api.contractocr.com/documentation"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint for monitoring"""
    from app.core.monitoring import get_health_metrics
    return await get_health_metrics()


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring (Prometheus format)"""
    if not settings.ENABLE_METRICS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    from app.core.monitoring import resource_monitor
    metrics = await resource_monitor.get_system_metrics()
    
    # Simple Prometheus-style metrics
    prometheus_metrics = f"""# HELP cpu_usage_percent CPU usage percentage
# TYPE cpu_usage_percent gauge
cpu_usage_percent {metrics.get('cpu', {}).get('percent', 0)}

# HELP memory_usage_percent Memory usage percentage  
# TYPE memory_usage_percent gauge
memory_usage_percent {metrics.get('memory', {}).get('percent', 0)}

# HELP disk_usage_percent Disk usage percentage
# TYPE disk_usage_percent gauge
disk_usage_percent {metrics.get('disk', {}).get('percent', 0)}

# HELP process_count Number of processes
# TYPE process_count gauge
process_count {metrics.get('processes', 0)}
"""
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(prometheus_metrics, media_type="text/plain")


@app.get("/")
async def root():
    """Root endpoint - redirect to documentation"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")


@app.get("/documentation")
async def documentation():
    """Redirect to complete API documentation"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/integration/documentation")
