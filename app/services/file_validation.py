"""
File validation service for PDF documents
"""
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

import PyPDF2
from io import BytesIO
from typing import Optional, Dict, Any
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class ValidationResult:
    """Result of file validation"""
    is_valid: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    page_count: Optional[int] = None
    file_size: Optional[int] = None


class FileValidationService:
    """Service for validating uploaded PDF files"""
    
    def __init__(self):
        self.max_file_size = settings.MAX_FILE_SIZE
        self.max_pages = settings.MAX_PAGES
    
    def validate_pdf(
        self, 
        file_content: bytes, 
        filename: str,
        max_size: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate PDF file content and metadata
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            max_size: Maximum allowed file size (defaults to settings)
            
        Returns:
            ValidationResult with validation status and details
        """
        max_size = max_size or self.max_file_size
        
        # Check file size
        file_size = len(file_content)
        if file_size == 0:
            return ValidationResult(
                is_valid=False,
                error_code="EMPTY_FILE",
                error_message="Uploaded file is empty",
                file_size=file_size
            )
        
        if file_size > max_size:
            return ValidationResult(
                is_valid=False,
                error_code="FILE_TOO_LARGE",
                error_message=f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)",
                details={
                    "file_size": file_size,
                    "max_size": max_size,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                    "max_size_mb": round(max_size / (1024 * 1024), 2)
                },
                file_size=file_size
            )
        
        # Check file format using python-magic (if available)
        if MAGIC_AVAILABLE:
            try:
                file_type = magic.from_buffer(file_content, mime=True)
                if file_type != "application/pdf":
                    return ValidationResult(
                        is_valid=False,
                        error_code="INVALID_FILE_FORMAT",
                        error_message="The uploaded file is not a valid PDF document",
                        details={
                            "file_type_detected": file_type,
                            "expected_type": "application/pdf",
                            "filename": filename
                        },
                        file_size=file_size
                    )
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_code="FILE_TYPE_DETECTION_ERROR",
                    error_message=f"Could not detect file type: {str(e)}",
                    file_size=file_size
                )
        else:
            # Fallback: Check if file starts with PDF signature
            if not file_content.startswith(b'%PDF-'):
                return ValidationResult(
                    is_valid=False,
                    error_code="INVALID_FILE_FORMAT",
                    error_message="The uploaded file is not a valid PDF document (PDF signature not found)",
                    details={
                        "file_type_detected": "unknown",
                        "expected_type": "application/pdf",
                        "filename": filename,
                        "note": "libmagic not available, using basic PDF signature check"
                    },
                    file_size=file_size
                )
        
        # Validate PDF structure and get page count
        try:
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_content))
            page_count = len(pdf_reader.pages)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                return ValidationResult(
                    is_valid=False,
                    error_code="ENCRYPTED_PDF",
                    error_message="Encrypted PDF files are not supported",
                    details={
                        "filename": filename,
                        "page_count": page_count
                    },
                    file_size=file_size,
                    page_count=page_count
                )
            
            # Check page count limit
            if page_count > self.max_pages:
                return ValidationResult(
                    is_valid=False,
                    error_code="TOO_MANY_PAGES",
                    error_message=f"PDF has {page_count} pages, maximum allowed is {self.max_pages}",
                    details={
                        "page_count": page_count,
                        "max_pages": self.max_pages,
                        "filename": filename
                    },
                    file_size=file_size,
                    page_count=page_count
                )
            
            # Check for completely empty PDF
            if page_count == 0:
                return ValidationResult(
                    is_valid=False,
                    error_code="EMPTY_PDF",
                    error_message="PDF document contains no pages",
                    details={
                        "filename": filename
                    },
                    file_size=file_size,
                    page_count=page_count
                )
            
            # Try to read first page to check for corruption
            try:
                first_page = pdf_reader.pages[0]
                # Attempt to extract text to verify page is readable
                first_page.extract_text()
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    error_code="CORRUPTED_PDF",
                    error_message="PDF appears to be corrupted or unreadable",
                    details={
                        "filename": filename,
                        "page_count": page_count,
                        "corruption_error": str(e)
                    },
                    file_size=file_size,
                    page_count=page_count
                )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_code="PDF_VALIDATION_ERROR",
                error_message=f"Failed to validate PDF structure: {str(e)}",
                details={
                    "filename": filename,
                    "validation_error": str(e)
                },
                file_size=file_size
            )
        
        # All validations passed
        return ValidationResult(
            is_valid=True,
            page_count=page_count,
            file_size=file_size
        )
    
    def validate_filename(self, filename: str) -> ValidationResult:
        """
        Validate filename format and extension
        
        Args:
            filename: Original filename
            
        Returns:
            ValidationResult with validation status
        """
        if not filename:
            return ValidationResult(
                is_valid=False,
                error_code="MISSING_FILENAME",
                error_message="Filename is required"
            )
        
        # Check file extension
        if not filename.lower().endswith('.pdf'):
            return ValidationResult(
                is_valid=False,
                error_code="INVALID_FILE_EXTENSION",
                error_message="File must have .pdf extension",
                details={
                    "filename": filename,
                    "expected_extension": ".pdf"
                }
            )
        
        # Check for potentially dangerous characters
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            return ValidationResult(
                is_valid=False,
                error_code="UNSAFE_FILENAME",
                error_message="Filename contains unsafe characters",
                details={
                    "filename": filename,
                    "dangerous_chars": [char for char in dangerous_chars if char in filename]
                }
            )
        
        return ValidationResult(is_valid=True)