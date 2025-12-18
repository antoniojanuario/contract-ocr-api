"""
Page-based content organization service for contract documents.

This service handles:
- Page extraction logic to maintain page-to-text mapping
- Coordinate tracking for text blocks within pages
- Table and list structure detection and preservation
- Cross-reference link detection between pages
- JSON response structure with page indices and metadata
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum
import json
from collections import defaultdict

from app.models.schemas import PageContent, TextBlock, BoundingBox, DocumentMetadata, ProcessingResult

logger = logging.getLogger(__name__)


@dataclass
class TableStructure:
    """Represents a detected table structure."""
    page_number: int
    bounding_box: BoundingBox
    rows: int
    columns: int
    cells: List[List[str]] 


@dataclass
class ListStructure:
    """Represents a detected list structure."""
    page_number: int
    bounding_box: BoundingBox
    list_type: str  # "ordered", "unordered", "definition"
    items: List[str]
    indentation_level: int


@dataclass
class CrossReference:
    """Represents a cross-reference between pages."""
    source_page: int
    target_page: int
    reference_text: str
    reference_type: str  # "clause", "section", "page", "article"


class StructureType(Enum):
    """Types of document structures that can be detected."""
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST = "list"
    TABLE = "table"
    CLAUSE = "clause"
    SIGNATURE = "signature"
    FOOTER = "footer"
    HEADER = "header"


class PageOrganizer:
    """
    Organizes extracted text content by pages with structure preservation.
    
    This class handles the organization of OCR-extracted text into a structured
    format that maintains page boundaries, text positioning, and document structure.
    """
    
    def __init__(self):
        self.clause_patterns = [
            r'^\d+\.\s+',  # 1. Clause
            r'^\d+\.\d+\s+',  # 1.1 Sub-clause
            r'^\d+\.\d+\.\d+\s+',  # 1.1.1 Sub-sub-clause
            r'^[A-Z]\.\s+',  # A. Section
            r'^\([a-z]\)\s+',  # (a) Item
            r'^\([0-9]+\)\s+',  # (1) Numbered item
        ]
        
        self.list_patterns = [
            r'^\s*[-•*]\s+',  # Bullet points
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[a-z]\)\s+',  # Lettered lists
            r'^\s*[ivx]+\.\s+',  # Roman numerals
        ]
        
        self.cross_ref_patterns = [
            r'(?:cláusula|clause|section|artigo|article)\s+(\d+(?:\.\d+)*)',
            r'(?:página|page)\s+(\d+)',
            r'(?:item|alínea)\s+([a-z]|\d+)',
            r'(?:anexo|appendix)\s+([A-Z]|\d+)',
        ]

    def organize_pages(self, ocr_results: List[Dict], metadata: DocumentMetadata) -> ProcessingResult:
        """
        Organize OCR results into structured page content.
        
        Args:
            ocr_results: List of OCR results per page
            metadata: Document metadata
            
        Returns:
            ProcessingResult with organized page content
        """
        try:
            pages = []
            cross_references = []
            
            for page_idx, page_data in enumerate(ocr_results):
                page_number = page_idx + 1
                
                # Extract text blocks with coordinates
                text_blocks = self._extract_text_blocks(page_data, page_number)
                
                # Detect structures (tables, lists, etc.)
                tables = self._detect_tables(text_blocks, page_number)
                lists = self._detect_lists(text_blocks, page_number)
                
                # Generate raw and normalized text
                raw_text = self._generate_raw_text(text_blocks)
                normalized_text = self._normalize_page_text(raw_text)
                
                # Detect cross-references
                page_cross_refs = self._detect_cross_references(normalized_text, page_number)
                cross_references.extend(page_cross_refs)
                
                # Create page content
                page_content = PageContent(
                    page_number=page_number,
                    text_blocks=text_blocks,
                    raw_text=raw_text,
                    normalized_text=normalized_text,
                    tables=[self._table_to_dict(table) for table in tables],
                    images=page_data.get('images', [])
                )
                
                pages.append(page_content)
            
            # Add cross-reference metadata
            metadata_dict = metadata.dict()
            metadata_dict['cross_references'] = [
                {
                    'source_page': ref.source_page,
                    'target_page': ref.target_page,
                    'reference_text': ref.reference_text,
                    'reference_type': ref.reference_type
                }
                for ref in cross_references
            ]
            
            return ProcessingResult(
                document_id=metadata.document_id,
                status="completed",
                progress=100,
                pages=pages,
                metadata=metadata,
                error_message=None,
                legal_terms=self._extract_legal_terms_from_pages(pages)
            )
            
        except Exception as e:
            logger.error(f"Error organizing pages: {str(e)}")
            raise

    def _extract_text_blocks(self, page_data: Dict, page_number: int) -> List[TextBlock]:
        """Extract text blocks with bounding boxes from page data."""
        text_blocks = []
        
        # Handle different OCR engine outputs
        if 'blocks' in page_data:
            # EasyOCR format
            for block in page_data['blocks']:
                bbox = self._normalize_bounding_box(block.get('bbox', [0, 0, 0, 0]))
                
                text_block = TextBlock(
                    text=block.get('text', '').strip(),
                    confidence=float(block.get('confidence', 0.0)),
                    bounding_box=bbox,
                    font_size=block.get('font_size'),
                    is_title=self._is_title_text(block.get('text', ''), bbox)
                )
                
                if text_block.text:  # Only add non-empty blocks
                    text_blocks.append(text_block)
                    
        elif 'text_blocks' in page_data:
            # Already processed format
            for block_data in page_data['text_blocks']:
                text_blocks.append(TextBlock(**block_data))
        
        # Sort blocks by reading order (top to bottom, left to right)
        text_blocks.sort(key=lambda b: (b.bounding_box.y, b.bounding_box.x))
        
        return text_blocks

    def _normalize_bounding_box(self, bbox: List[float]) -> BoundingBox:
        """Normalize bounding box coordinates."""
        if len(bbox) >= 4:
            return BoundingBox(
                x=float(bbox[0]),
                y=float(bbox[1]),
                width=float(bbox[2] - bbox[0]) if len(bbox) == 4 else float(bbox[2]),
                height=float(bbox[3] - bbox[1]) if len(bbox) == 4 else float(bbox[3])
            )
        return BoundingBox(x=0.0, y=0.0, width=0.0, height=0.0)

    def _is_title_text(self, text: str, bbox: BoundingBox) -> bool:
        """Determine if text block is likely a title or heading."""
        if not text:
            return False
            
        # Check for title patterns
        title_patterns = [
            r'^[A-Z\s]+$',  # All caps$',  # All caps
            r'^\d+\.\s*[A-Z]',  # Numbered section
            r'^CLÁUSULA|^ARTIGO|^CAPÍTULO|^SEÇÃO',  # Legal document sections
            r'^CONTRATO|^ACORDO|^TERMO',  # Contract titles
        ]
        
        for pattern in title_patterns:
            if re.match(pattern, text.strip()):
                return True
                
        # Check font size if available (titles usually larger)
        if bbox.height > 20:  # Assuming larger text height indicates title
            return True
            
        return False

    def _detect_tables(self, text_blocks: List[TextBlock], page_number: int) -> List[TableStructure]:
        """Detect table structures in text blocks."""
        tables = []
        
        # Group text blocks that might form tables
        potential_table_blocks = []
        current_y = None
        current_row_blocks = []
        
        for block in text_blocks:
            # If blocks are roughly on the same horizontal line, they might be table cells
            if current_y is None or abs(block.bounding_box.y - current_y) < 10:
                current_row_blocks.append(block)
                current_y = block.bounding_box.y
            else:
                if len(current_row_blocks) > 1:  # Potential table row
                    potential_table_blocks.append(current_row_blocks)
                current_row_blocks = [block]
                current_y = block.bounding_box.y
        
        # Add last row
        if len(current_row_blocks) > 1:
            potential_table_blocks.append(current_row_blocks)
        
        # Analyze potential table blocks
        if len(potential_table_blocks) >= 2:  # At least 2 rows for a table
            # Check if columns align
            for i in range(len(potential_table_blocks) - 1):
                current_row = potential_table_blocks[i]
                next_row = potential_table_blocks[i + 1]
                
                if len(current_row) == len(next_row):  # Same number of columns
                    # Check column alignment
                    aligned = True
                    for j in range(len(current_row)):
                        x_diff = abs(current_row[j].bounding_box.x - next_row[j].bounding_box.x)
                        if x_diff > 20:  # Allow some tolerance
                            aligned = False
                            break
                    
                    if aligned:
                        # Create table structure
                        all_blocks = current_row + next_row
                        min_x = min(b.bounding_box.x for b in all_blocks)
                        min_y = min(b.bounding_box.y for b in all_blocks)
                        max_x = max(b.bounding_box.x + b.bounding_box.width for b in all_blocks)
                        max_y = max(b.bounding_box.y + b.bounding_box.height for b in all_blocks)
                        
                        table_bbox = BoundingBox(
                            x=min_x,
                            y=min_y,
                            width=max_x - min_x,
                            height=max_y - min_y
                        )
                        
                        cells = []
                        cells.append([block.text for block in current_row])
                        cells.append([block.text for block in next_row])
                        
                        table = TableStructure(
                            page_number=page_number,
                            bounding_box=table_bbox,
                            rows=2,
                            columns=len(current_row),
                            cells=cells
                        )
                        tables.append(table)
        
        return tables

    def _detect_lists(self, text_blocks: List[TextBlock], page_number: int) -> List[ListStructure]:
        """Detect list structures in text blocks."""
        lists = []
        current_list_items = []
        current_list_type = None
        current_indentation = None
        
        for block in text_blocks:
            text = block.text.strip()
            
            # Check if this block starts a list item
            list_match = None
            detected_type = None
            
            for pattern in self.list_patterns:
                match = re.match(pattern, text)
                if match:
                    list_match = match
                    if '•' in pattern or '*' in pattern or '-' in pattern:
                        detected_type = "unordered"
                    elif r'\d+\.' in pattern:
                        detected_type = "ordered"
                    else:
                        detected_type = "ordered"
                    break
            
            if list_match:
                # Calculate indentation level
                indentation = len(text) - len(text.lstrip())
                
                # If this is a new list or different indentation
                if (current_list_type != detected_type or 
                    current_indentation != indentation or 
                    not current_list_items):
                    
                    # Save previous list if exists
                    if current_list_items:
                        lists.append(self._create_list_structure(
                            current_list_items, page_number, current_list_type, current_indentation
                        ))
                    
                    # Start new list
                    current_list_items = [text]
                    current_list_type = detected_type
                    current_indentation = indentation
                else:
                    # Continue current list
                    current_list_items.append(text)
            else:
                # Not a list item, save current list if exists
                if current_list_items:
                    lists.append(self._create_list_structure(
                        current_list_items, page_number, current_list_type, current_indentation
                    ))
                    current_list_items = []
                    current_list_type = None
                    current_indentation = None
        
        # Save final list if exists
        if current_list_items:
            lists.append(self._create_list_structure(
                current_list_items, page_number, current_list_type, current_indentation
            ))
        
        return lists

    def _create_list_structure(self, items: List[str], page_number: int, 
                             list_type: str, indentation: int) -> ListStructure:
        """Create a ListStructure from detected items."""
        return ListStructure(
            page_number=page_number,
            bounding_box=BoundingBox(x=0, y=0, width=0, height=0),  # Would need actual coordinates
            list_type=list_type,
            items=items,
            indentation_level=indentation
        )

    def _detect_cross_references(self, text: str, page_number: int) -> List[CrossReference]:
        """Detect cross-references to other parts of the document."""
        cross_refs = []
        
        for pattern in self.cross_ref_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                ref_text = match.group(0)
                target_info = match.group(1)
                
                # Determine reference type and target
                ref_type = "clause"
                target_page = page_number  # Default to current page
                
                if "página" in ref_text.lower() or "page" in ref_text.lower():
                    ref_type = "page"
                    try:
                        target_page = int(target_info)
                    except ValueError:
                        continue
                elif "artigo" in ref_text.lower() or "article" in ref_text.lower():
                    ref_type = "article"
                elif "anexo" in ref_text.lower() or "appendix" in ref_text.lower():
                    ref_type = "appendix"
                
                cross_ref = CrossReference(
                    source_page=page_number,
                    target_page=target_page,
                    reference_text=ref_text,
                    reference_type=ref_type
                )
                cross_refs.append(cross_ref)
        
        return cross_refs

    def _generate_raw_text(self, text_blocks: List[TextBlock]) -> str:
        """Generate raw text from text blocks maintaining structure."""
        if not text_blocks:
            return ""
        
        # Sort blocks by reading order
        sorted_blocks = sorted(text_blocks, key=lambda b: (b.bounding_box.y, b.bounding_box.x))
        
        lines = []
        current_line_y = None
        current_line_blocks = []
        
        for block in sorted_blocks:
            # Group blocks that are on the same line
            if current_line_y is None or abs(block.bounding_box.y - current_line_y) < 10:
                current_line_blocks.append(block)
                current_line_y = block.bounding_box.y
            else:
                # Process current line
                if current_line_blocks:
                    line_text = " ".join(b.text for b in sorted(current_line_blocks, 
                                                              key=lambda x: x.bounding_box.x))
                    lines.append(line_text)
                
                # Start new line
                current_line_blocks = [block]
                current_line_y = block.bounding_box.y
        
        # Add final line
        if current_line_blocks:
            line_text = " ".join(b.text for b in sorted(current_line_blocks, 
                                                      key=lambda x: x.bounding_box.x))
            lines.append(line_text)
        
        return "\n".join(lines)

    def _normalize_page_text(self, raw_text: str) -> str:
        """Apply basic normalization to page text."""
        if not raw_text:
            return ""
        
        # Remove excessive whitespace
        normalized = re.sub(r'\s+', ' ', raw_text)
        
        # Fix common OCR errors
        normalized = re.sub(r'([a-z])([A-Z])', r'\1 \2', normalized)  # Add space between words
        normalized = re.sub(r'(\d+)([A-Za-z])', r'\1 \2', normalized)  # Space after numbers
        
        # Preserve paragraph structure
        normalized = re.sub(r'\n\s*\n', '\n\n', normalized)
        
        return normalized.strip()

    def _table_to_dict(self, table: TableStructure) -> Dict:
        """Convert TableStructure to dictionary for JSON serialization."""
        return {
            'page_number': table.page_number,
            'bounding_box': {
                'x': table.bounding_box.x,
                'y': table.bounding_box.y,
                'width': table.bounding_box.width,
                'height': table.bounding_box.height
            },
            'rows': table.rows,
            'columns': table.columns,
            'cells': table.cells
        }

    def _extract_legal_terms_from_pages(self, pages: List[PageContent]) -> List[str]:
        """Extract legal terms from all pages."""
        legal_terms = set()
        
        # Common legal terms in Portuguese and English
        legal_patterns = [
            r'\b(?:contrato|contract|acordo|agreement)\b',
            r'\b(?:cláusula|clause|artigo|article)\b',
            r'\b(?:parte|party|partes|parties)\b',
            r'\b(?:obrigação|obligation|direito|right)\b',
            r'\b(?:garantia|warranty|fiança|surety)\b',
            r'\b(?:rescisão|termination|resolução|resolution)\b',
            r'\b(?:multa|penalty|indenização|indemnification)\b',
        ]
        
        for page in pages:
            text = page.normalized_text.lower()
            for pattern in legal_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                legal_terms.update(matches)
        
        return sorted(list(legal_terms))

    def get_page_structure_info(self, page_content: PageContent) -> Dict[str, Any]:
        """Get detailed structure information for a page."""
        structure_info = {
            'page_number': page_content.page_number,
            'total_text_blocks': len(page_content.text_blocks),
            'total_tables': len(page_content.tables),
            'has_titles': any(block.is_title for block in page_content.text_blocks),
            'confidence_stats': {
                'min': min((block.confidence for block in page_content.text_blocks), default=0),
                'max': max((block.confidence for block in page_content.text_blocks), default=0),
                'avg': sum(block.confidence for block in page_content.text_blocks) / len(page_content.text_blocks) if page_content.text_blocks else 0
            },
            'text_density': len(page_content.normalized_text) / max(1, len(page_content.text_blocks)),
            'structure_types': self._identify_structure_types(page_content)
        }
        
        return structure_info

    def _identify_structure_types(self, page_content: PageContent) -> List[str]:
        """Identify types of structures present on the page."""
        structures = []
        
        text = page_content.normalized_text
        
        # Check for different structure types
        if any(block.is_title for block in page_content.text_blocks):
            structures.append("headings")
        
        if page_content.tables:
            structures.append("tables")
        
        # Check for clauses
        for pattern in self.clause_patterns:
            if re.search(pattern, text, re.MULTILINE):
                structures.append("clauses")
                break
        
        # Check for lists
        for pattern in self.list_patterns:
            if re.search(pattern, text, re.MULTILINE):
                structures.append("lists")
                break
        
        # Check for signatures
        if re.search(r'assinatura|signature|_+|\.{3,}', text, re.IGNORECASE):
            structures.append("signatures")
        
        return structures