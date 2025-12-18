"""
API v1 router configuration
"""
from fastapi import APIRouter
from app.api.v1.endpoints import documents, integration, copilot

api_router = APIRouter()

# Include document endpoints
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

# Include integration endpoints
api_router.include_router(integration.router, prefix="/integration", tags=["integration"])

# Include Copilot Studio endpoints
api_router.include_router(copilot.router, prefix="/copilot", tags=["copilot-studio"])