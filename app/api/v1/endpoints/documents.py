"""
Document upload and management endpoints
"""
import os
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, Request, Path
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from app.core.config import settings
from app.models.schemas import (
    DocumentUploadResponse, 
    DocumentStatusResponse, 
    ProcessingResult,
    ErrorResponse,
    ProcessingStatus
)
from app.models.database import Document
from app.db.base import get_db
from app.services.file_storage import FileStorageService
from app.services.file_validation import FileValidationService
from app.core.security import verify_api_key

router = APIRouter()

# Initialize services
file_storage = FileStorageService()
file_validator = FileValidationService()

# Setup logger
logger = logging.getLogger(__name__)


from app.core.errors import ErrorCode, ValidationError, NotFoundError, ProcessingError
from app.core.alerting import track_error_for_alerting
from app.middleware.request_logging import get_request_id
from app.middleware.error_handler import create_error_response


@router.post("/upload", 
    response_model=DocumentUploadResponse,
    summary="Upload PDF Document for OCR Processing",
    description="""
    Upload a PDF document for OCR processing and text extraction.
    
    The document will be queued for asynchronous processing using multiple OCR engines
    for maximum accuracy. Processing typically takes 1-5 minutes depending on document
    size and complexity.
    
    **File Requirements:**
    - Format: PDF only
    - Size: Maximum 50MB
    - Pages: Up to 100 pages
    - Quality: Standard resolution recommended for best results
    
    **Processing Pipeline:**
    1. File validation and format verification
    2. Multi-engine OCR processing (EasyOCR, PaddleOCR, Tesseract)
    3. Text normalization and legal term processing
    4. Page-based content organization
    5. Results storage and notification
    
    **Returns:**
    - Unique document ID for tracking
    - Initial processing status (queued)
    - Success message
    """,
    responses={
        200: {
            "description": "Document uploaded successfully",
            "content": {
                "application/json": {
                    "example": {
                        "document_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "queued",
                        "message": "Document uploaded successfully and queued for processing"
                    }
                }
            }
        },
        400: {
            "description": "Invalid file or validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "file_too_large": {
                            "summary": "File size exceeds limit",
                            "value": {
                                "error": {
                                    "code": "FILE_TOO_LARGE",
                                    "message": "File size exceeds maximum limit of 50MB",
                                    "details": {"file_size": 52428800, "max_size": 50000000}
                                }
                            }
                        },
                        "invalid_format": {
                            "summary": "Invalid file format",
                            "value": {
                                "error": {
                                    "code": "INVALID_FILE_FORMAT",
                                    "message": "Only PDF files are supported",
                                    "details": {"detected_format": "image/jpeg", "expected_format": "application/pdf"}
                                }
                            }
                        },
                        "corrupted_pdf": {
                            "summary": "Corrupted PDF file",
                            "value": {
                                "error": {
                                    "code": "CORRUPTED_PDF",
                                    "message": "PDF file appears to be corrupted or unreadable",
                                    "details": {"validation_error": "Unable to read PDF structure"}
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_API_KEY",
                            "message": "API key is required for authentication"
                        }
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Rate limit exceeded. Maximum 60 requests per minute."
                        }
                    }
                }
            }
        }
    }
)
async def upload_document(
    request: Request,
    file: UploadFile = File(
        ...,
        description="PDF document to process",
        media_type="application/pdf"
    ),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Read file content
        file_content = await file.read()
        
        # Validate file
        validation_result = file_validator.validate_pdf(
            file_content=file_content,
            filename=file.filename or "unknown.pdf",
            max_size=settings.MAX_FILE_SIZE
        )
        
        if not validation_result.is_valid:
            request_id = get_request_id(request) if 'request' in locals() else None
            track_error_for_alerting(validation_result.error_code, request_id)
            
            return create_error_response(
                code=ErrorCode(validation_result.error_code),
                message=validation_result.error_message,
                details=validation_result.details,
                request_id=request_id
            )
        
        # Store file
        file_path = await file_storage.save_document(
            file_content=file_content,
            document_id=document_id,
            filename=file.filename or "unknown.pdf"
        )
        
        # Create database record
        db_document = Document(
            id=document_id,
            filename=file.filename or "unknown.pdf",
            file_size=len(file_content),
            status=ProcessingStatus.QUEUED.value,
            progress=0,
            page_count=validation_result.page_count,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        
        # Add to processing queue
        from app.services.task_worker import enqueue_document_processing
        queue_success = await enqueue_document_processing(
            document_id=document_id,
            filename=file.filename or "unknown.pdf",
            file_path=file_path
        )
        
        if not queue_success:
            logger.warning(f"Failed to enqueue document {document_id} for processing")
        
        return DocumentUploadResponse(
            document_id=document_id,
            status=ProcessingStatus.QUEUED,
            message="Document uploaded successfully and queued for processing"
        )
        
    except Exception as e:
        # Clean up any stored files on error
        try:
            if 'file_path' in locals():
                await file_storage.delete_document(document_id)
        except:
            pass
        
        request_id = get_request_id(request) if 'request' in locals() else None
        track_error_for_alerting("UPLOAD_ERROR", request_id, {"error": str(e)})
        
        logger.error(
            f"Document upload failed: {str(e)}",
            extra={
                "document_id": document_id,
                "filename": file.filename,
                "request_id": request_id
            },
            exc_info=True
        )
        
        return create_error_response(
            code=ErrorCode.UPLOAD_ERROR,
            message=f"Failed to upload document: {str(e)}",
            request_id=request_id
        )


@router.get("/{document_id}/status", 
    response_model=DocumentStatusResponse,
    summary="Get Document Processing Status",
    description="""
    Retrieve the current processing status and progress for a document.
    
    Use this endpoint to poll for processing completion. Recommended polling
    interval is 10-30 seconds to balance responsiveness with API efficiency.
    
    **Status Values:**
    - `queued`: Document is waiting to be processed (0% progress)
    - `processing`: OCR and text extraction in progress (1-99% progress)
    - `completed`: Processing finished successfully (100% progress)
    - `failed`: Processing failed with error (see error_message)
    
    **Typical Processing Times:**
    - 1-5 pages: 30-60 seconds
    - 6-20 pages: 1-3 minutes
    - 21-50 pages: 3-7 minutes
    - 51-100 pages: 7-15 minutes
    
    **Best Practices:**
    - Poll every 10-30 seconds during processing
    - Set reasonable timeouts (5-10 minutes for large documents)
    - Handle both completed and failed statuses appropriately
    """,
    responses={
        200: {
            "description": "Status retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "queued": {
                            "summary": "Document queued for processing",
                            "value": {
                                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                                "status": "queued",
                                "progress": 0,
                                "message": "Document is queued",
                                "error_message": None
                            }
                        },
                        "processing": {
                            "summary": "Document being processed",
                            "value": {
                                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                                "status": "processing",
                                "progress": 45,
                                "message": "Document is processing",
                                "error_message": None
                            }
                        },
                        "completed": {
                            "summary": "Processing completed successfully",
                            "value": {
                                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                                "status": "completed",
                                "progress": 100,
                                "message": "Document is completed",
                                "error_message": None
                            }
                        },
                        "failed": {
                            "summary": "Processing failed with error",
                            "value": {
                                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                                "status": "failed",
                                "progress": 0,
                                "message": "Document is failed",
                                "error_message": "OCR processing failed: corrupted PDF structure"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Invalid document ID format",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "INVALID_DOCUMENT_ID",
                            "message": "Invalid document ID format. Must be a valid UUID."
                        }
                    }
                }
            }
        },
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DOCUMENT_NOT_FOUND",
                            "message": "Document with ID 123e4567-e89b-12d3-a456-426614174000 not found"
                        }
                    }
                }
            }
        }
    }
)
async def get_document_status(
    request: Request,
    document_id: str = Path(
        ...,
        description="Unique document identifier (UUID format)",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        # Validate document ID format
        uuid.UUID(document_id)
    except ValueError:
        request_id = get_request_id(request)
        return create_error_response(
            code=ErrorCode.INVALID_DOCUMENT_ID,
            message="Invalid document ID format",
            request_id=request_id
        )
    
    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        request_id = get_request_id(request)
        return create_error_response(
            code=ErrorCode.DOCUMENT_NOT_FOUND,
            message=f"Document with ID {document_id} not found",
            request_id=request_id
        )
    
    return DocumentStatusResponse(
        document_id=document_id,
        status=ProcessingStatus(document.status),
        progress=document.progress or 0,
        message=f"Document is {document.status}",
        error_message=document.error_message
    )


@router.get("/{document_id}/results", 
    response_model=ProcessingResult,
    summary="Get Document Processing Results",
    description="""
    Retrieve the complete processing results for a successfully processed document.
    
    This endpoint returns the extracted and normalized text content organized by pages,
    along with comprehensive metadata about the processing operation.
    
    **Only available for documents with status = 'completed'**
    
    **Response Structure:**
    - **pages**: Array of page objects with text blocks and coordinates
    - **metadata**: Document information and processing statistics
    - **legal_terms**: Extracted legal terminology and key phrases
    
    **Text Block Information:**
    - Raw OCR text and normalized/cleaned text
    - Confidence scores for accuracy assessment
    - Bounding box coordinates for precise positioning
    - Title/heading detection for document structure
    
    **Use Cases:**
    - Contract analysis and term extraction
    - Document search and indexing
    - Legal document processing workflows
    - Content management system integration
    """,
    responses={
        200: {
            "description": "Processing results retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "document_id": "123e4567-e89b-12d3-a456-426614174000",
                        "status": "completed",
                        "progress": 100,
                        "pages": [
                            {
                                "page_number": 1,
                                "text_blocks": [
                                    {
                                        "text": "CONTRACT AGREEMENT",
                                        "confidence": 0.98,
                                        "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 30},
                                        "font_size": 16.0,
                                        "is_title": True
                                    },
                                    {
                                        "text": "This agreement is made between the parties...",
                                        "confidence": 0.95,
                                        "bounding_box": {"x": 50, "y": 100, "width": 500, "height": 200},
                                        "font_size": 12.0,
                                        "is_title": False
                                    }
                                ],
                                "raw_text": "CONTRACT AGREEMENT\n\nThis agreement is made between the parties...",
                                "normalized_text": "CONTRACT AGREEMENT\n\nThis agreement is made between the parties...",
                                "tables": [],
                                "images": []
                            }
                        ],
                        "metadata": {
                            "document_id": "123e4567-e89b-12d3-a456-426614174000",
                            "filename": "contract.pdf",
                            "file_size": 1048576,
                            "page_count": 5,
                            "processing_time": 45.2,
                            "ocr_confidence": 0.95,
                            "created_at": "2024-01-15T10:00:00Z",
                            "updated_at": "2024-01-15T10:01:00Z"
                        },
                        "error_message": None,
                        "legal_terms": ["agreement", "contract", "party", "terms", "conditions", "liability"]
                    }
                }
            }
        },
        400: {
            "description": "Processing not completed or invalid request",
            "content": {
                "application/json": {
                    "examples": {
                        "not_completed": {
                            "summary": "Document processing not completed",
                            "value": {
                                "error": {
                                    "code": "PROCESSING_NOT_COMPLETED",
                                    "message": "Document processing is processing. Results not available yet."
                                }
                            }
                        },
                        "invalid_id": {
                            "summary": "Invalid document ID format",
                            "value": {
                                "error": {
                                    "code": "INVALID_DOCUMENT_ID",
                                    "message": "Invalid document ID format. Must be a valid UUID."
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DOCUMENT_NOT_FOUND",
                            "message": "Document with ID 123e4567-e89b-12d3-a456-426614174000 not found"
                        }
                    }
                }
            }
        }
    }
)
async def get_document_results(
    document_id: str = Path(
        ...,
        description="Unique document identifier (UUID format)",
        example="123e4567-e89b-12d3-a456-426614174000"
    ),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    try:
        # Validate document ID format
        uuid.UUID(document_id)
    except ValueError:
        return create_error_response(
            code="INVALID_DOCUMENT_ID",
            message="Invalid document ID format"
        )
    
    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        return create_error_response(
            code="DOCUMENT_NOT_FOUND",
            message=f"Document with ID {document_id} not found"
        )
    
    if document.status != ProcessingStatus.COMPLETED.value:
        return create_error_response(
            code="PROCESSING_NOT_COMPLETED",
            message=f"Document processing is {document.status}. Results not available yet."
        )
    
    # Load actual processing results from database
    from app.models.schemas import DocumentMetadata, PageContent, TextBlock, BoundingBox
    from app.models.database import Page, TextBlock as DBTextBlock
    
    # Get pages from database
    pages = db.query(Page).filter(Page.document_id == document_id).order_by(Page.page_number).all()
    
    # Convert pages to response format
    page_contents = []
    legal_terms_set = set()
    
    for page in pages:
        # Get text blocks for this page
        text_blocks = db.query(DBTextBlock).filter(DBTextBlock.page_id == page.id).all()
        
        # Convert text blocks to response format
        response_text_blocks = []
        for block in text_blocks:
            bounding_box = BoundingBox(
                x=block.x,
                y=block.y,
                width=block.width,
                height=block.height
            )
            
            text_block = TextBlock(
                text=block.text,
                confidence=block.confidence,
                bounding_box=bounding_box,
                font_size=block.font_size,
                is_title=block.is_title
            )
            response_text_blocks.append(text_block)
        
        # Extract legal terms from text (simple keyword extraction)
        if page.raw_text:
            legal_keywords = [
                "contrato", "acordo", "partes", "cláusula", "condições", "termos",
                "responsabilidade", "obrigação", "direitos", "deveres", "pagamento",
                "prazo", "vencimento", "garantia", "fiança", "avalista", "crédito",
                "empréstimo", "financiamento", "juros", "taxa", "multa", "penalidade"
            ]
            
            text_lower = page.raw_text.lower()
            for keyword in legal_keywords:
                if keyword in text_lower:
                    legal_terms_set.add(keyword)
        
        # Create page content
        page_content = PageContent(
            page_number=page.page_number,
            raw_text=page.raw_text or "",
            normalized_text=page.normalized_text or page.raw_text or "",
            text_blocks=response_text_blocks,
            tables=page.page_metadata.get("tables", []) if page.page_metadata else [],
            images=page.page_metadata.get("images", []) if page.page_metadata else []
        )
        page_contents.append(page_content)
    
    # Create metadata
    metadata = DocumentMetadata(
        document_id=document_id,
        filename=document.filename,
        file_size=document.file_size,
        page_count=document.page_count or len(page_contents),
        processing_time=document.processing_time,
        ocr_confidence=document.ocr_confidence,
        created_at=document.created_at,
        updated_at=document.updated_at
    )
    
    return ProcessingResult(
        document_id=document_id,
        status=ProcessingStatus(document.status),
        progress=document.progress or 0,
        pages=page_contents,
        metadata=metadata,
        error_message=document.error_message,
        legal_terms=list(legal_terms_set)
    )


@router.get("/history", response_model=list)
async def get_processing_history(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get processing history for documents
    
    - **limit**: Maximum number of documents to return (default: 50, max: 100)
    - **offset**: Number of documents to skip (default: 0)
    - **status**: Filter by processing status (optional)
    
    Returns list of document processing history
    """
    # Validate limit
    limit = min(limit, 100)  # Cap at 100 for performance
    
    # Build query
    query = db.query(Document).order_by(Document.created_at.desc())
    
    # Apply status filter if provided
    if status:
        if status not in ['queued', 'processing', 'completed', 'failed']:
            return create_error_response(
                code="INVALID_STATUS_FILTER",
                message=f"Invalid status filter: {status}. Must be one of: queued, processing, completed, failed"
            )
        query = query.filter(Document.status == status)
    
    # Apply pagination
    documents = query.offset(offset).limit(limit).all()
    
    # Convert to response format
    history = []
    for doc in documents:
        history.append({
            "document_id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "progress": doc.progress or 0,
            "file_size": doc.file_size,
            "page_count": doc.page_count,
            "processing_time": doc.processing_time,
            "ocr_confidence": doc.ocr_confidence,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "error_message": doc.error_message
        })
    
    return history


@router.get("/{document_id}/metadata")
async def get_document_metadata(
    document_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get detailed metadata for a document
    
    - **document_id**: Unique document identifier
    
    Returns comprehensive document metadata including processing statistics
    """
    try:
        # Validate document ID format
        uuid.UUID(document_id)
    except ValueError:
        return create_error_response(
            code="INVALID_DOCUMENT_ID",
            message="Invalid document ID format"
        )
    
    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        return create_error_response(
            code="DOCUMENT_NOT_FOUND",
            message=f"Document with ID {document_id} not found"
        )
    
    # Get related pages and text blocks for additional metadata
    from app.models.database import Page, TextBlock
    pages = db.query(Page).filter(Page.document_id == document_id).all()
    
    total_text_blocks = 0
    total_confidence_sum = 0.0
    confidence_count = 0
    
    for page in pages:
        text_blocks = db.query(TextBlock).filter(TextBlock.page_id == page.id).all()
        total_text_blocks += len(text_blocks)
        
        for block in text_blocks:
            if block.confidence is not None:
                total_confidence_sum += block.confidence
                confidence_count += 1
    
    avg_block_confidence = total_confidence_sum / confidence_count if confidence_count > 0 else None
    
    metadata = {
        "document_id": document.id,
        "filename": document.filename,
        "file_size": document.file_size,
        "status": document.status,
        "progress": document.progress or 0,
        "page_count": document.page_count,
        "processing_time": document.processing_time,
        "ocr_confidence": document.ocr_confidence,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "error_message": document.error_message,
        "legal_terms": document.legal_terms or [],
        "statistics": {
            "total_pages_processed": len(pages),
            "total_text_blocks": total_text_blocks,
            "average_block_confidence": avg_block_confidence,
            "processing_duration_seconds": document.processing_time,
            "file_size_mb": round(document.file_size / (1024 * 1024), 2) if document.file_size else 0
        }
    }
    
    return metadata


@router.post("/{document_id}/webhook")
async def configure_webhook(
    document_id: str,
    webhook_config: dict,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Configure webhook notification for document processing completion
    
    - **document_id**: Unique document identifier
    - **webhook_config**: Webhook configuration including URL and events
    
    Configures webhook to be called when document processing completes
    """
    try:
        # Validate document ID format
        uuid.UUID(document_id)
    except ValueError:
        return create_error_response(
            code="INVALID_DOCUMENT_ID",
            message="Invalid document ID format"
        )
    
    # Validate webhook configuration
    if not webhook_config.get("url"):
        return create_error_response(
            code="MISSING_WEBHOOK_URL",
            message="Webhook URL is required"
        )
    
    webhook_url = webhook_config["url"]
    events = webhook_config.get("events", ["completed", "failed"])
    
    # Validate webhook URL format
    if not webhook_url.startswith(("http://", "https://")):
        return create_error_response(
            code="INVALID_WEBHOOK_URL",
            message="Webhook URL must start with http:// or https://"
        )
    
    # Get document from database
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        return create_error_response(
            code="DOCUMENT_NOT_FOUND",
            message=f"Document with ID {document_id} not found"
        )
    
    # Configure webhook using webhook service
    from app.services.webhook_service import get_webhook_service
    webhook_service = get_webhook_service()
    
    success = webhook_service.configure_webhook(
        document_id=document_id,
        webhook_url=webhook_url,
        events=events
    )
    
    if not success:
        return create_error_response(
            code="WEBHOOK_CONFIGURATION_FAILED",
            message="Failed to configure webhook"
        )
    return {
        "document_id": document_id,
        "webhook_configured": True,
        "webhook_url": webhook_url,
        "events": events,
        "message": "Webhook configured successfully"
    }


@router.get("/system/health")
async def system_health_check():
    """
    System health check endpoint for monitoring
    
    Returns system status and health metrics
    """
    from app.core.config import settings
    from app.db.base import get_db
    import os
    
    try:
        # Check database connectivity
        db_healthy = True
        db_error = None
        try:
            # Test database connection
            db = next(get_db())
            db.execute("SELECT 1")
            db.close()
        except Exception as e:
            db_healthy = False
            db_error = str(e)
        
        # Check system resources (if psutil is available)
        system_metrics = {}
        if PSUTIL_AVAILABLE:
            try:
                memory_usage = psutil.virtual_memory()
                disk_usage = psutil.disk_usage('/')
                cpu_percent = psutil.cpu_percent(interval=1)
                
                system_metrics = {
                    "memory_usage_percent": memory_usage.percent,
                    "memory_available_mb": round(memory_usage.available / (1024 * 1024), 2),
                    "disk_usage_percent": disk_usage.percent,
                    "disk_free_gb": round(disk_usage.free / (1024 * 1024 * 1024), 2),
                    "cpu_usage_percent": cpu_percent
                }
            except Exception as e:
                system_metrics = {"error": f"Failed to get system metrics: {str(e)}"}
        else:
            system_metrics = {"note": "System metrics unavailable (psutil not installed)"}
        
        # Check queue status (simplified)
        queue_healthy = True
        queue_error = None
        try:
            from app.services.task_queue import get_task_queue
            task_queue = await get_task_queue()
            # Basic queue health check
            if hasattr(task_queue, 'health_check'):
                queue_healthy = task_queue.health_check()
        except Exception as e:
            queue_healthy = False
            queue_error = str(e)
        
        # Determine overall health
        overall_healthy = db_healthy and queue_healthy
        
        health_data = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": settings.VERSION,
            "components": {
                "database": {
                    "status": "healthy" if db_healthy else "unhealthy",
                    "error": db_error
                },
                "task_queue": {
                    "status": "healthy" if queue_healthy else "unhealthy", 
                    "error": queue_error
                }
            },
            "system_metrics": system_metrics
        }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": f"Health check failed: {str(e)}",
            "version": settings.VERSION
        }