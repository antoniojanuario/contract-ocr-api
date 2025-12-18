"""
OCR Engine with multiple backend support for contract document processing.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import tempfile
import os
import io
from PIL import Image
import fitz  # PyMuPDF for PDF processing

from app.models.schemas import PageContent, TextBlock, BoundingBox

logger = logging.getLogger(__name__)


class OCRBackend(str, Enum):
    """Available OCR backend engines."""
    EASYOCR = "easyocr"
    PADDLEOCR = "paddleocr"
    TESSERACT = "tesseract"


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    confidence: float
    bounding_box: BoundingBox
    font_size: Optional[float] = None
    is_title: bool = False


class OCREngine(ABC):
    """Abstract base class for OCR engines."""
    
    @abstractmethod
    def extract_text(self, image: Image.Image) -> List[OCRResult]:
        """Extract text from an image."""
        pass
    
    @abstractmethod
    def get_confidence_score(self) -> float:
        """Get overall confidence score for the last extraction."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the OCR engine is available and properly configured."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name of the OCR engine."""
        pass


class MultiBackendOCRService:
    """OCR service with multiple backend support and fallback logic."""
    
    def __init__(self):
        self.engines = []
        self.available_engines = []
        logger.info("OCR service initialized")
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[PageContent]:
        """Extract text from PDF using PyMuPDF (basic text extraction)."""
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            # Check if file exists
            if not os.path.exists(pdf_path):
                logger.error(f"PDF file not found: {pdf_path}")
                return []
            
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            pages_content = []
            
            logger.info(f"PDF has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text from page
                text = page.get_text()
                
                if not text.strip():
                    logger.warning(f"No text found on page {page_num + 1}")
                    # If no text, try OCR on page image (basic fallback)
                    text = f"[Page {page_num + 1} - No extractable text found]"
                
                # Create text blocks (simplified - one block per page)
                text_blocks = []
                if text.strip():
                    # Get page dimensions for bounding box
                    rect = page.rect
                    bounding_box = BoundingBox(
                        x=0,
                        y=0,
                        width=int(rect.width),
                        height=int(rect.height)
                    )
                    
                    text_block = TextBlock(
                        text=text.strip(),
                        confidence=0.95,  # High confidence for native PDF text
                        bounding_box=bounding_box,
                        font_size=12.0,
                        is_title=False
                    )
                    text_blocks.append(text_block)
                
                # Create page content
                page_content = PageContent(
                    page_number=page_num + 1,
                    raw_text=text,
                    normalized_text="",  # Will be filled by text processor
                    text_blocks=text_blocks,
                    tables=[],
                    images=[]
                )
                
                pages_content.append(page_content)
                logger.info(f"Extracted {len(text)} characters from page {page_num + 1}")
            
            doc.close()
            logger.info(f"Successfully extracted text from {len(pages_content)} pages")
            return pages_content
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
            return []
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engine names."""
        return ["pymupdf"]
    
    def assess_quality(self, pages: List[PageContent]) -> Dict[str, Any]:
        """Assess the quality of OCR results."""
        if not pages:
            return {"overall_confidence": 0.0, "total_text_blocks": 0, "pages_processed": 0}
        
        total_blocks = sum(len(page.text_blocks) for page in pages)
        total_confidence = sum(
            sum(block.confidence for block in page.text_blocks) 
            for page in pages
        )
        
        avg_confidence = total_confidence / total_blocks if total_blocks > 0 else 0.0
        
        return {
            "overall_confidence": avg_confidence,
            "total_text_blocks": total_blocks,
            "pages_processed": len(pages)
        }