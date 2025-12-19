"""
Hybrid OCR Engine that handles both native text PDFs and scanned image PDFs
"""
import logging
import time
import io
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image

# PDF libraries
try:
    import pdfplumber
    PDF_LIBRARY = "pdfplumber"
except ImportError:
    try:
        import pypdf
        PDF_LIBRARY = "pypdf"
    except ImportError:
        PDF_LIBRARY = None

# OCR libraries for image processing
OCR_LIBRARY = None
try:
    import easyocr
    OCR_LIBRARY = "easyocr"
except ImportError:
    try:
        import pytesseract
        OCR_LIBRARY = "tesseract"
    except ImportError:
        pass

from app.models.schemas import PageContent, TextBlock, BoundingBox

logger = logging.getLogger(__name__)


class HybridOCREngine:
    """
    Hybrid OCR Engine that can handle:
    1. Native text PDFs (fast extraction)
    2. Scanned image PDFs (OCR processing)
    3. Mixed PDFs (combination of both)
    """
    
    def __init__(self):
        self.confidence_threshold = 0.7
        self.ocr_reader = None
        self._initialize_ocr()
        
    def _initialize_ocr(self):
        """Initialize OCR engine if available"""
        try:
            if OCR_LIBRARY == "easyocr":
                self.ocr_reader = easyocr.Reader(['pt', 'en'])  # Portuguese and English
                logger.info("EasyOCR initialized for Portuguese and English")
            elif OCR_LIBRARY == "tesseract":
                # Test if tesseract is available
                import pytesseract
                pytesseract.get_tesseract_version()
                logger.info("Tesseract OCR available")
            else:
                logger.warning("No OCR library available - only native text extraction will work")
        except Exception as e:
            logger.warning(f"OCR initialization failed: {e}")
            self.ocr_reader = None
    
    def extract_text_from_pdf(self, pdf_path: str) -> List[PageContent]:
        """
        Extract text from PDF using hybrid approach:
        1. Try native text extraction first (fast)
        2. If no text found, use OCR on images (slower but comprehensive)
        """
        try:
            logger.info(f"Starting hybrid extraction for: {pdf_path}")
            
            if PDF_LIBRARY == "pdfplumber":
                return self._extract_with_pdfplumber_hybrid(pdf_path)
            elif PDF_LIBRARY == "pypdf":
                return self._extract_with_pypdf_hybrid(pdf_path)
            else:
                logger.warning("No PDF library available")
                return self._create_placeholder_content(pdf_path)
                
        except Exception as e:
            logger.error(f"Hybrid OCR extraction failed: {str(e)}")
            return self._create_placeholder_content(pdf_path)
    
    def _extract_with_pdfplumber_hybrid(self, pdf_path: str) -> List[PageContent]:
        """Extract text using pdfplumber with OCR fallback"""
        pages_content = []
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Processing PDF with {len(pdf.pages)} pages using hybrid pdfplumber")
            
            for page_num, page in enumerate(pdf.pages):
                # Step 1: Try native text extraction
                raw_text = page.extract_text() or ""
                text_blocks = []
                
                if raw_text.strip():
                    # Native text found - use it
                    logger.info(f"Page {page_num + 1}: Native text found ({len(raw_text)} chars)")
                    text_blocks = self._create_text_blocks_from_text(raw_text, confidence=0.95)
                else:
                    # Step 2: No native text - try OCR on page image
                    logger.info(f"Page {page_num + 1}: No native text, attempting OCR")
                    
                    try:
                        # Convert page to image
                        page_image = page.to_image(resolution=150)  # Good balance of quality/speed
                        pil_image = page_image.original
                        
                        # Perform OCR
                        ocr_result = self._perform_ocr(pil_image)
                        if ocr_result:
                            raw_text = ocr_result['text']
                            text_blocks = ocr_result['blocks']
                            logger.info(f"Page {page_num + 1}: OCR extracted {len(raw_text)} chars")
                        else:
                            raw_text = f"[Page {page_num + 1} - No text could be extracted]"
                            logger.warning(f"Page {page_num + 1}: OCR failed")
                            
                    except Exception as e:
                        logger.error(f"Page {page_num + 1}: OCR processing failed: {e}")
                        raw_text = f"[Page {page_num + 1} - OCR processing failed]"
                
                # Create page content
                page_content = PageContent(
                    page_number=page_num + 1,
                    raw_text=raw_text,
                    normalized_text="",
                    text_blocks=text_blocks,
                    tables=[],
                    images=[]
                )
                pages_content.append(page_content)
        
        logger.info(f"Hybrid extraction completed: {len(pages_content)} pages processed")
        return pages_content
    
    def _extract_with_pypdf_hybrid(self, pdf_path: str) -> List[PageContent]:
        """Extract text using pypdf with OCR fallback"""
        from pypdf import PdfReader
        import fitz  # PyMuPDF for image extraction
        
        pages_content = []
        
        # Use PyMuPDF for image extraction when needed
        pdf_doc = fitz.open(pdf_path) if OCR_LIBRARY else None
        
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            logger.info(f"Processing PDF with {len(reader.pages)} pages using hybrid pypdf")
            
            for page_num, page in enumerate(reader.pages):
                # Step 1: Try native text extraction
                raw_text = page.extract_text()
                text_blocks = []
                
                if raw_text and raw_text.strip():
                    # Native text found
                    logger.info(f"Page {page_num + 1}: Native text found ({len(raw_text)} chars)")
                    text_blocks = self._create_text_blocks_from_text(raw_text, confidence=0.90)
                else:
                    # Step 2: Try OCR if available
                    logger.info(f"Page {page_num + 1}: No native text, attempting OCR")
                    
                    if pdf_doc and OCR_LIBRARY:
                        try:
                            # Get page as image using PyMuPDF
                            page_fitz = pdf_doc[page_num]
                            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
                            pix = page_fitz.get_pixmap(matrix=mat)
                            img_data = pix.tobytes("png")
                            pil_image = Image.open(io.BytesIO(img_data))
                            
                            # Perform OCR
                            ocr_result = self._perform_ocr(pil_image)
                            if ocr_result:
                                raw_text = ocr_result['text']
                                text_blocks = ocr_result['blocks']
                                logger.info(f"Page {page_num + 1}: OCR extracted {len(raw_text)} chars")
                            else:
                                raw_text = f"[Page {page_num + 1} - No text could be extracted]"
                                
                        except Exception as e:
                            logger.error(f"Page {page_num + 1}: OCR processing failed: {e}")
                            raw_text = f"[Page {page_num + 1} - OCR processing failed]"
                    else:
                        raw_text = f"[Page {page_num + 1} - No text extraction available]"
                
                # Create page content
                page_content = PageContent(
                    page_number=page_num + 1,
                    raw_text=raw_text or "",
                    normalized_text="",
                    text_blocks=text_blocks,
                    tables=[],
                    images=[]
                )
                pages_content.append(page_content)
        
        if pdf_doc:
            pdf_doc.close()
            
        logger.info(f"Hybrid extraction completed: {len(pages_content)} pages processed")
        return pages_content
    
    def _perform_ocr(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """Perform OCR on a PIL image"""
        if not OCR_LIBRARY:
            return None
            
        try:
            if OCR_LIBRARY == "easyocr" and self.ocr_reader:
                # Convert PIL to numpy array
                import numpy as np
                img_array = np.array(image)
                
                # Perform OCR
                results = self.ocr_reader.readtext(img_array)
                
                # Process results
                text_parts = []
                text_blocks = []
                
                for (bbox, text, confidence) in results:
                    if confidence > self.confidence_threshold:
                        text_parts.append(text)
                        
                        # Create bounding box
                        x_coords = [point[0] for point in bbox]
                        y_coords = [point[1] for point in bbox]
                        
                        bounding_box = BoundingBox(
                            x=min(x_coords),
                            y=min(y_coords),
                            width=max(x_coords) - min(x_coords),
                            height=max(y_coords) - min(y_coords)
                        )
                        
                        text_block = TextBlock(
                            text=text,
                            confidence=confidence,
                            bounding_box=bounding_box,
                            font_size=12.0,
                            is_title=len(text) < 50 and text.isupper()
                        )
                        text_blocks.append(text_block)
                
                return {
                    'text': '\n'.join(text_parts),
                    'blocks': text_blocks
                }
                
            elif OCR_LIBRARY == "tesseract":
                import pytesseract
                
                # Perform OCR
                text = pytesseract.image_to_string(image, lang='por+eng')
                
                if text.strip():
                    text_blocks = self._create_text_blocks_from_text(text, confidence=0.85)
                    return {
                        'text': text,
                        'blocks': text_blocks
                    }
                    
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            
        return None
    
    def _create_text_blocks_from_text(self, text: str, confidence: float = 0.95) -> List[TextBlock]:
        """Create text blocks from plain text"""
        text_blocks = []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        y_pos = 0
        
        for line in lines:
            bounding_box = BoundingBox(
                x=0,
                y=y_pos,
                width=min(len(line) * 8, 500),  # Estimate width based on character count
                height=15
            )
            
            text_block = TextBlock(
                text=line,
                confidence=confidence,
                bounding_box=bounding_box,
                font_size=12.0,
                is_title=len(line) < 50 and any(c.isupper() for c in line)
            )
            text_blocks.append(text_block)
            y_pos += 20
            
        return text_blocks
    
    def _create_placeholder_content(self, pdf_path: str) -> List[PageContent]:
        """Create placeholder content when extraction fails"""
        logger.warning("Creating placeholder content - PDF processing not available")
        
        bounding_box = BoundingBox(x=0, y=0, width=500, height=50)
        
        text_block = TextBlock(
            text="PDF processing not available. Please ensure the PDF contains readable text or images.",
            confidence=1.0,
            bounding_box=bounding_box,
            font_size=12.0,
            is_title=False
        )
        
        page_content = PageContent(
            page_number=1,
            raw_text="PDF processing not available.",
            normalized_text="",
            text_blocks=[text_block],
            tables=[],
            images=[]
        )
        
        return [page_content]
    
    def get_available_engines(self) -> List[str]:
        """Get list of available engines"""
        engines = []
        if PDF_LIBRARY:
            engines.append(f"{PDF_LIBRARY}_native")
        if OCR_LIBRARY:
            engines.append(f"{OCR_LIBRARY}_ocr")
        if not engines:
            engines.append("placeholder")
        return engines
    
    def assess_quality(self, pages: List[PageContent]) -> Dict[str, Any]:
        """Assess the quality of OCR results"""
        if not pages:
            return {
                "overall_confidence": 0.0, 
                "total_text_blocks": 0, 
                "pages_processed": 0,
                "engines_used": []
            }
        
        total_blocks = sum(len(page.text_blocks) for page in pages)
        total_confidence = sum(
            sum(block.confidence for block in page.text_blocks) 
            for page in pages
        )
        
        avg_confidence = total_confidence / total_blocks if total_blocks > 0 else 0.0
        
        # Analyze text extraction methods used
        native_pages = sum(1 for page in pages if page.raw_text and not page.raw_text.startswith('[Page'))
        ocr_pages = len(pages) - native_pages
        
        return {
            "overall_confidence": avg_confidence,
            "total_text_blocks": total_blocks,
            "pages_processed": len(pages),
            "native_text_pages": native_pages,
            "ocr_pages": ocr_pages,
            "engines_available": self.get_available_engines(),
            "pdf_library": PDF_LIBRARY,
            "ocr_library": OCR_LIBRARY
        }