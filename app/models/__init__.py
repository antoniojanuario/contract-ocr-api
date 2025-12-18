# Data models package

# Import Pydantic models (schemas)
from .schemas import (
    ProcessingStatus,
    BoundingBox,
    TextBlock,
    PageContent,
    DocumentMetadata,
    ProcessingResult,
    DocumentUploadResponse,
    DocumentStatusResponse,
    ErrorResponse
)

# Import SQLAlchemy models (database)
from .database import (
    Document,
    Page,
    TextBlock as DBTextBlock
)

__all__ = [
    # Pydantic models
    "ProcessingStatus",
    "BoundingBox", 
    "TextBlock",
    "PageContent",
    "DocumentMetadata",
    "ProcessingResult",
    "DocumentUploadResponse",
    "DocumentStatusResponse",
    "ErrorResponse",
    # SQLAlchemy models
    "Document",
    "Page", 
    "DBTextBlock"
]