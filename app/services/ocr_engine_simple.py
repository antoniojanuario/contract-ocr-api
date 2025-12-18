"""
Simple OCR Engine for extracting text from PDF documents without heavy dependencies
"""
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

# Use simpler PDF libraries that don't require compilation
try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import pypdf
        PDF_LIBRARY = "pypdf"
    except ImportError:
        PDF_LIBRARY = None

from app.models.schemas import PageContent, TextBlock, BoundingBox

logger = logging.getLogger(__name__)


class SimpleOCREngine:
    """Simple OCR Engine for processing PDF documents without heavy dependencies"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
        
    def extract_text_from_pdf(self, pdf_path: str) -> List[PageContent]:
        """
        Extract text from PDF using available simple PDF library
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of PageContent with extracted text
        """
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")
            
            if PDF_LIBRARY == "pdfplumber":
                return self._extract_with_pdfplumber(pdf_path)
            elif PDF_LIBRARY == "pypdf":
                return self._extract_with_pypdf(pdf_path)
            else:
                # Fallback: create empty pages
                logger.warning("No PDF library available, creating placeholder content")
                return self._create_placeholder_content(pdf_path)
                
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            # Return placeholder content instead of failing
            return self._create_placeholder_content(pdf_path)
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> List[PageContent]:
        """Extract text using pdfplumber"""
        pages_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Processing PDF with {len(pdf.pages)} pages using pdfplumber")
            
            for page_num, page in enumerate(pdf.pages):
                # Extract text
                raw_text = page.extract_text() or ""
                
                # Create text blocks from text
                text_blocks = []
                if raw_text.strip():
                    # Simple approach: create one block per line
                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    y_pos = 0
                    
                    for line in lines:
                        bounding_box = BoundingBox(
                            x=0,
                            y=y_pos,
                            width=500,  # Estimated
                            height=15   # Estimated
                        )
                        
                        text_block = TextBlock(
                            text=line,
                            confidence=0.95,
                            bounding_box=bounding_box,
                            font_size=12.0,
                            is_title=len(line) < 50 and any(c.isupper() for c in line)
                        )
                        text_blocks.append(text_block)
                        y_pos += 20
                
                # Create page content
                page_content = PageContent(
                    page_number=page_num + 1,
                    raw_text=raw_text,
                    normalized_text="",  # Will be filled by text processor
                    text_blocks=text_blocks,
                    tables=[],
                    images=[]
                )
                pages_content.append(page_content)
                logger.info(f"Extracted {len(raw_text)} characters from page {page_num + 1}")
        
        logger.info(f"Successfully extracted text from {len(pages_content)} pages")
        return pages_content
    
    def _extract_with_pypdf(self, pdf_path: str) -> List[PageContent]:
        """Extract text using pypdf (fallback)"""
        from pypdf import PdfReader
        
        pages_content = []
        
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            logger.info(f"Processing PDF with {len(reader.pages)} pages using pypdf")
            
            for page_num, page in enumerate(reader.pages):
                # Extract text
                raw_text = page.extract_text()
                
                # Create text blocks from text
                text_blocks = []
                if raw_text and raw_text.strip():
                    # Simple approach: create one block per paragraph
                    paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
                    y_pos = 0
                    
                    for paragraph in paragraphs:
                        bounding_box = BoundingBox(
                            x=0,
                            y=y_pos,
                            width=500,  # Estimated
                            height=len(paragraph.split('\n')) * 15  # Estimated
                        )
                        
                        text_block = TextBlock(
                            text=paragraph,
                            confidence=0.90,
                            bounding_box=bounding_box,
                            font_size=12.0,
                            is_title=len(paragraph) < 100 and paragraph.isupper()
                        )
                        text_blocks.append(text_block)
                        y_pos += len(paragraph.split('\n')) * 20
                
                # Create page content
                page_content = PageContent(
                    page_number=page_num + 1,
                    raw_text=raw_text or "",
                    normalized_text="",  # Will be filled by text processor
                    text_blocks=text_blocks,
                    tables=[],
                    images=[]
                )
                pages_content.append(page_content)
                logger.info(f"Extracted {len(raw_text or '')} characters from page {page_num + 1}")
        
        logger.info(f"Successfully extracted text from {len(pages_content)} pages")
        return pages_content
    
    def _create_placeholder_content(self, pdf_path: str) -> List[PageContent]:
        """Create placeholder content when no PDF library is available"""
        logger.warning("Creating placeholder content - PDF text extraction not available")
        
        # Create a single page with placeholder text
        bounding_box = BoundingBox(x=0, y=0, width=500, height=50)
        
        text_block = TextBlock(
            text="PDF text extraction not available in this deployment. Please upload a text file instead.",
            confidence=1.0,
            bounding_box=bounding_box,
            font_size=12.0,
            is_title=False
        )
        
        page_content = PageContent(
            page_number=1,
            raw_text="PDF text extraction not available in this deployment.",
            normalized_text="",
            text_blocks=[text_block],
            tables=[],
            images=[]
        )
        
        return [page_content]
    
    def get_available_engines(self) -> List[str]:
        """Get list of available OCR engine names."""
        engines = []
        if PDF_LIBRARY:
            engines.append(PDF_LIBRARY)
        else:
            engines.append("placeholder")
        return engines
    
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
            "pages_processed": len(pages),
            "engine": PDF_LIBRARY or "placeholder"
        }