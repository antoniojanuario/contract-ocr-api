"""
Unit tests for database models
"""
import pytest
from sqlalchemy.orm import Session
from app.db.base import SessionLocal, engine
from app.models.database import Document, Page, TextBlock
from app.models.schemas import ProcessingStatus
import uuid


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_document_creation(db_session: Session):
    """Test creating a document in the database"""
    document = Document(
        filename="test_contract.pdf",
        file_size=1024000,
        status="queued",
        page_count=5
    )
    
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    
    assert document.id is not None
    assert document.filename == "test_contract.pdf"
    assert document.file_size == 1024000
    assert document.status == "queued"
    assert document.page_count == 5
    assert document.created_at is not None
    assert document.updated_at is not None


def test_page_creation_with_document(db_session: Session):
    """Test creating a page associated with a document"""
    # Create document first
    document = Document(
        filename="test_contract.pdf",
        file_size=1024000,
        status="processing",
        page_count=1
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    
    # Create page
    page = Page(
        document_id=document.id,
        page_number=1,
        raw_text="This is raw text from OCR",
        normalized_text="This is normalized text",
        confidence=0.95
    )
    
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)
    
    assert page.id is not None
    assert page.document_id == document.id
    assert page.page_number == 1
    assert page.raw_text == "This is raw text from OCR"
    assert page.normalized_text == "This is normalized text"
    assert page.confidence == 0.95


def test_text_block_creation_with_page(db_session: Session):
    """Test creating a text block associated with a page"""
    # Create document and page first
    document = Document(
        filename="test_contract.pdf",
        file_size=1024000,
        status="processing",
        page_count=1
    )
    db_session.add(document)
    db_session.commit()
    
    page = Page(
        document_id=document.id,
        page_number=1,
        raw_text="Contract text",
        normalized_text="Contract text"
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)
    
    # Create text block
    text_block = TextBlock(
        page_id=page.id,
        text="CONTRATO DE PRESTAÇÃO DE SERVIÇOS",
        confidence=0.98,
        x=100.0,
        y=200.0,
        width=300.0,
        height=50.0,
        font_size=14.0,
        is_title=True
    )
    
    db_session.add(text_block)
    db_session.commit()
    db_session.refresh(text_block)
    
    assert text_block.id is not None
    assert text_block.page_id == page.id
    assert text_block.text == "CONTRATO DE PRESTAÇÃO DE SERVIÇOS"
    assert text_block.confidence == 0.98
    assert text_block.x == 100.0
    assert text_block.y == 200.0
    assert text_block.width == 300.0
    assert text_block.height == 50.0
    assert text_block.font_size == 14.0
    assert text_block.is_title is True


def test_document_page_relationship(db_session: Session):
    """Test the relationship between document and pages"""
    # Create document with pages
    document = Document(
        filename="multi_page_contract.pdf",
        file_size=2048000,
        status="completed",
        page_count=3
    )
    db_session.add(document)
    db_session.commit()
    
    # Create multiple pages
    for i in range(1, 4):
        page = Page(
            document_id=document.id,
            page_number=i,
            raw_text=f"Page {i} content",
            normalized_text=f"Page {i} content"
        )
        db_session.add(page)
    
    db_session.commit()
    db_session.refresh(document)
    
    # Test relationship
    assert len(document.pages) == 3
    assert document.pages[0].page_number == 1
    assert document.pages[1].page_number == 2
    assert document.pages[2].page_number == 3
    
    # Test back reference
    for page in document.pages:
        assert page.document.id == document.id


def test_page_text_block_relationship(db_session: Session):
    """Test the relationship between page and text blocks"""
    # Create document and page
    document = Document(
        filename="test_contract.pdf",
        file_size=1024000,
        status="completed",
        page_count=1
    )
    db_session.add(document)
    db_session.commit()
    
    page = Page(
        document_id=document.id,
        page_number=1,
        raw_text="Page with multiple text blocks",
        normalized_text="Page with multiple text blocks"
    )
    db_session.add(page)
    db_session.commit()
    db_session.refresh(page)
    
    # Create multiple text blocks
    text_blocks_data = [
        {"text": "Title", "x": 100, "y": 50, "is_title": True},
        {"text": "Paragraph 1", "x": 100, "y": 100, "is_title": False},
        {"text": "Paragraph 2", "x": 100, "y": 150, "is_title": False}
    ]
    
    for block_data in text_blocks_data:
        text_block = TextBlock(
            page_id=page.id,
            text=block_data["text"],
            confidence=0.95,
            x=block_data["x"],
            y=block_data["y"],
            width=200.0,
            height=30.0,
            is_title=block_data["is_title"]
        )
        db_session.add(text_block)
    
    db_session.commit()
    db_session.refresh(page)
    
    # Test relationship
    assert len(page.text_blocks) == 3
    assert page.text_blocks[0].text == "Title"
    assert page.text_blocks[0].is_title is True
    assert page.text_blocks[1].text == "Paragraph 1"
    assert page.text_blocks[1].is_title is False
    
    # Test back reference
    for text_block in page.text_blocks:
        assert text_block.page.id == page.id