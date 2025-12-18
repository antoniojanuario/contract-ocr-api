"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base
import uuid


class Document(Base):
    """Document table for storing document metadata and processing status"""
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="queued", index=True)
    progress = Column(Integer, default=0)
    page_count = Column(Integer, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    processing_time = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    legal_terms = Column(JSON, nullable=True)  # Store as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"


class Page(Base):
    """Page table for storing page-level content and metadata"""
    __tablename__ = "pages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    normalized_text = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    page_metadata = Column(JSON, nullable=True)  # Store tables, images, etc. as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="pages")
    text_blocks = relationship("TextBlock", back_populates="page", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Page(id={self.id}, document_id={self.document_id}, page_number={self.page_number})>"


class TextBlock(Base):
    """Text block table for storing individual text blocks with position data"""
    __tablename__ = "text_blocks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    page_id = Column(String, ForeignKey("pages.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    font_size = Column(Float, nullable=True)
    is_title = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    page = relationship("Page", back_populates="text_blocks")
    
    def __repr__(self):
        return f"<TextBlock(id={self.id}, page_id={self.page_id}, text='{self.text[:50]}...')>"


class TaskRecord(Base):
    """Task record table for storing task queue information"""
    __tablename__ = "task_records"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    payload = Column(Text, nullable=False)  # JSON string
    progress = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<TaskRecord(id={self.id}, document_id={self.document_id}, status={self.status})>"


# Index definitions for better query performance
from sqlalchemy import Index

# Composite indexes for common queries
Index('idx_document_status_created', Document.status, Document.created_at)
Index('idx_page_document_number', Page.document_id, Page.page_number)
Index('idx_textblock_page_position', TextBlock.page_id, TextBlock.y, TextBlock.x)
Index('idx_task_status_created', TaskRecord.status, TaskRecord.created_at)
Index('idx_task_document_status', TaskRecord.document_id, TaskRecord.status)