"""
Pydantic models for API requests and responses
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class ProcessingStatus(str, Enum):
    """Document processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BoundingBox(BaseModel):
    """Bounding box coordinates for text blocks"""
    x: float = Field(..., description="X coordinate of top-left corner")
    y: float = Field(..., description="Y coordinate of top-left corner")
    width: float = Field(..., description="Width of bounding box")
    height: float = Field(..., description="Height of bounding box")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "x": 100.5,
            "y": 200.3,
            "width": 300.0,
            "height": 50.0
        }
    })


class TextBlock(BaseModel):
    """Individual text block with position and metadata"""
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score")
    bounding_box: BoundingBox = Field(..., description="Position of text block")
    font_size: Optional[float] = Field(None, description="Estimated font size")
    is_title: bool = Field(False, description="Whether this block is a title/heading")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "text": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS",
            "confidence": 0.95,
            "bounding_box": {
                "x": 100.5,
                "y": 200.3,
                "width": 300.0,
                "height": 50.0
            },
            "font_size": 14.0,
            "is_title": True
        }
    })


class PageContent(BaseModel):
    """Content extracted from a single page"""
    page_number: int = Field(..., ge=1, description="Page number (1-indexed)")
    text_blocks: List[TextBlock] = Field(default_factory=list, description="Text blocks on this page")
    raw_text: str = Field(..., description="Raw extracted text")
    normalized_text: str = Field(..., description="Normalized and cleaned text")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Detected tables")
    images: List[Dict[str, Any]] = Field(default_factory=list, description="Detected images")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "page_number": 1,
            "text_blocks": [
                {
                    "text": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS",
                    "confidence": 0.95,
                    "bounding_box": {"x": 100.5, "y": 200.3, "width": 300.0, "height": 50.0},
                    "font_size": 14.0,
                    "is_title": True
                }
            ],
            "raw_text": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\n\nCláusula 1...",
            "normalized_text": "CONTRATO DE PRESTAÇÃO DE SERVIÇOS\n\nCláusula 1...",
            "tables": [],
            "images": []
        }
    })


class DocumentMetadata(BaseModel):
    """Metadata for a processed document"""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    page_count: int = Field(..., ge=0, description="Number of pages")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    ocr_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average OCR confidence")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "filename": "contract_2024.pdf",
            "file_size": 1048576,
            "page_count": 10,
            "processing_time": 45.5,
            "ocr_confidence": 0.92,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:31:00Z"
        }
    })


class ProcessingResult(BaseModel):
    """Complete processing result for a document"""
    document_id: str = Field(..., description="Unique document identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    progress: int = Field(0, ge=0, le=100, description="Processing progress percentage")
    pages: List[PageContent] = Field(default_factory=list, description="Extracted page content")
    metadata: DocumentMetadata = Field(..., description="Document metadata")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    legal_terms: List[str] = Field(default_factory=list, description="Detected legal terms")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "completed",
            "progress": 100,
            "pages": [],
            "metadata": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "contract_2024.pdf",
                "file_size": 1048576,
                "page_count": 10,
                "processing_time": 45.5,
                "ocr_confidence": 0.92,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:31:00Z"
            },
            "error_message": None,
            "legal_terms": ["contrato", "cláusula", "partes"]
        }
    })


# Request/Response models for API endpoints

class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    document_id: str = Field(..., description="Unique document identifier")
    status: ProcessingStatus = Field(..., description="Initial processing status")
    message: str = Field(..., description="Status message")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "queued",
            "message": "Document uploaded successfully and queued for processing"
        }
    })


class DocumentStatusResponse(BaseModel):
    """Response for status check"""
    document_id: str = Field(..., description="Unique document identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    progress: int = Field(..., ge=0, le=100, description="Processing progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "document_id": "550e8400-e29b-41d4-a716-446655440000",
            "status": "processing",
            "progress": 45,
            "message": "Processing page 5 of 10",
            "error_message": None
        }
    })


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: Dict[str, Any] = Field(..., description="Error details")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": {
                "code": "INVALID_FILE_FORMAT",
                "message": "The uploaded file is not a valid PDF document",
                "details": {
                    "file_type_detected": "image/jpeg",
                    "expected_type": "application/pdf"
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123456"
            }
        }
    })
