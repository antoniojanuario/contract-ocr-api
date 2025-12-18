"""
Endpoints específicos para integração com Microsoft Copilot Studio
"""
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.database import Document
from app.models.schemas import ProcessingStatus
from app.services.file_storage import FileStorageService
from app.services.file_validation import FileValidationService
from app.services.task_worker import enqueue_document_processing

router = APIRouter()
file_storage = FileStorageService()
file_validator = FileValidationService()
logger = logging.getLogger(__name__)


@router.post("/extract-text")
async def extract_text_from_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF file to extract text from"),
    db: Session = Depends(get_db)
):
    """
    Simplified endpoint for Copilot Studio - Upload PDF and get text extraction
    
    This endpoint is optimized for Microsoft Copilot Studio integration:
    - Single endpoint for upload and processing
    - Simplified response format
    - Automatic text extraction
    - Returns document ID for status checking
    """
    try:
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Read and validate file
        file_content = await file.read()
        
        validation_result = file_validator.validate_pdf(
            file_content=file_content,
            filename=file.filename or "document.pdf",
            max_size=25 * 1024 * 1024  # 25MB limit for free tier
        )
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": validation_result.error_code,
                    "message": validation_result.error_message,
                    "details": validation_result.details
                }
            )
        
        # Store file
        file_path = await file_storage.save_document(
            file_content=file_content,
            document_id=document_id,
            filename=file.filename or "document.pdf"
        )
        
        # Create database record
        db_document = Document(
            id=document_id,
            filename=file.filename or "document.pdf",
            file_size=len(file_content),
            status=ProcessingStatus.QUEUED.value,
            progress=0,
            page_count=validation_result.page_count
        )
        
        db.add(db_document)
        db.commit()
        
        # Enqueue for processing
        await enqueue_document_processing(
            document_id=document_id,
            filename=file.filename or "document.pdf",
            file_path=file_path
        )
        
        return {
            "success": True,
            "document_id": document_id,
            "status": "queued",
            "message": "Document uploaded and queued for OCR processing",
            "estimated_processing_time": "30-180 seconds",
            "status_check_url": f"/api/v1/copilot/status/{document_id}",
            "results_url": f"/api/v1/copilot/text/{document_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Copilot extract-text failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "PROCESSING_ERROR",
                "message": f"Failed to process document: {str(e)}"
            }
        )


@router.get("/status/{document_id}")
async def get_processing_status(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Get processing status for Copilot Studio
    
    Returns simplified status information optimized for chatbot integration
    """
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_ID", "message": "Invalid document ID format"}
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Document not found"}
        )
    
    # Calculate estimated time remaining
    estimated_remaining = 0
    if document.status == "queued":
        estimated_remaining = 60  # 1 minute
    elif document.status == "processing":
        estimated_remaining = max(30 - (document.progress or 0) // 3, 5)  # Based on progress
    
    return {
        "document_id": document_id,
        "status": document.status,
        "progress": document.progress or 0,
        "is_complete": document.status == "completed",
        "is_failed": document.status == "failed",
        "estimated_remaining_seconds": estimated_remaining,
        "error_message": document.error_message,
        "page_count": document.page_count,
        "processing_time": document.processing_time
    }


@router.get("/text/{document_id}")
async def get_extracted_text(
    document_id: str,
    format: str = "combined",  # combined, pages, blocks
    db: Session = Depends(get_db)
):
    """
    Get extracted text for Copilot Studio
    
    Format options:
    - combined: All text in single string
    - pages: Text organized by pages
    - blocks: Detailed text blocks with coordinates
    """
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_ID", "message": "Invalid document ID format"}
        )
    
    document = db.query(Document).filter(Document.id == document_id).first()
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Document not found"}
        )
    
    if document.status != "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NOT_READY",
                "message": f"Document is {document.status}. Text not available yet.",
                "status": document.status,
                "progress": document.progress or 0
            }
        )
    
    # Get pages from database
    from app.models.database import Page, TextBlock as DBTextBlock
    pages = db.query(Page).filter(Page.document_id == document_id).order_by(Page.page_number).all()
    
    if not pages:
        return {
            "document_id": document_id,
            "text": "",
            "page_count": 0,
            "message": "No text content found"
        }
    
    # Format response based on requested format
    if format == "combined":
        # Combine all text into single string
        all_text = []
        for page in pages:
            if page.normalized_text:
                all_text.append(f"--- Página {page.page_number} ---")
                all_text.append(page.normalized_text)
                all_text.append("")  # Empty line between pages
        
        return {
            "document_id": document_id,
            "text": "\n".join(all_text),
            "page_count": len(pages),
            "format": "combined",
            "legal_terms": _extract_legal_terms(pages),
            "metadata": {
                "filename": document.filename,
                "processing_time": document.processing_time,
                "ocr_confidence": document.ocr_confidence
            }
        }
    
    elif format == "pages":
        # Return text organized by pages
        page_texts = []
        for page in pages:
            page_texts.append({
                "page_number": page.page_number,
                "text": page.normalized_text or page.raw_text or "",
                "confidence": page.confidence
            })
        
        return {
            "document_id": document_id,
            "pages": page_texts,
            "page_count": len(pages),
            "format": "pages",
            "legal_terms": _extract_legal_terms(pages)
        }
    
    else:  # blocks format
        # Return detailed text blocks
        page_blocks = []
        for page in pages:
            text_blocks = db.query(DBTextBlock).filter(DBTextBlock.page_id == page.id).all()
            
            blocks = []
            for block in text_blocks:
                blocks.append({
                    "text": block.text,
                    "confidence": block.confidence,
                    "position": {
                        "x": block.x,
                        "y": block.y,
                        "width": block.width,
                        "height": block.height
                    },
                    "font_size": block.font_size,
                    "is_title": block.is_title
                })
            
            page_blocks.append({
                "page_number": page.page_number,
                "text_blocks": blocks,
                "raw_text": page.raw_text,
                "normalized_text": page.normalized_text
            })
        
        return {
            "document_id": document_id,
            "pages": page_blocks,
            "page_count": len(pages),
            "format": "blocks"
        }


def _extract_legal_terms(pages) -> list:
    """Extract legal terms from pages"""
    legal_keywords = [
        "contrato", "acordo", "partes", "cláusula", "condições", "termos",
        "responsabilidade", "obrigação", "direitos", "deveres", "pagamento",
        "prazo", "vencimento", "garantia", "fiança", "avalista", "crédito",
        "empréstimo", "financiamento", "juros", "taxa", "multa", "penalidade"
    ]
    
    found_terms = set()
    for page in pages:
        if page.raw_text:
            text_lower = page.raw_text.lower()
            for keyword in legal_keywords:
                if keyword in text_lower:
                    found_terms.add(keyword)
    
    return list(found_terms)


@router.get("/health")
async def copilot_health_check():
    """Health check endpoint for Copilot Studio integration"""
    return {
        "status": "healthy",
        "service": "Contract OCR API",
        "version": "1.0.0",
        "endpoints": {
            "extract_text": "/api/v1/copilot/extract-text",
            "status": "/api/v1/copilot/status/{document_id}",
            "text": "/api/v1/copilot/text/{document_id}"
        },
        "limits": {
            "max_file_size": "25MB",
            "max_pages": 50,
            "processing_timeout": "3 minutes"
        }
    }