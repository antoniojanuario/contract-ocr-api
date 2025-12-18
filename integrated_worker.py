#!/usr/bin/env python3
"""
Worker integrado que reprocessa documentos presos e processa novos
"""
import asyncio
import sys
import os
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_worker import WorkerManager, enqueue_document_processing
from app.services.file_storage import FileStorageService
from app.db.base import get_db_session
from app.models.database import Document
from app.core.config import settings

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def requeue_stuck_documents():
    """Requeue documents that are stuck in queued status"""
    logger.info("🔄 Checking for stuck documents...")
    
    file_storage = FileStorageService()
    requeued_count = 0
    
    try:
        with get_db_session() as db:
            # Get all queued documents
            queued_docs = db.query(Document).filter(Document.status == "queued").all()
            
            logger.info(f"📋 Found {len(queued_docs)} documents in queued status")
            
            for doc in queued_docs:
                # Generate file path
                file_path = file_storage._generate_file_path(doc.id, doc.filename)
                full_path = os.path.join(file_storage.backend.base_path, file_path)
                
                if not os.path.exists(full_path):
                    logger.warning(f"File not found for document {doc.id}: {full_path}")
                    continue
                
                # Enqueue for processing
                success = await enqueue_document_processing(
                    document_id=doc.id,
                    filename=doc.filename,
                    file_path=full_path
                )
                
                if success:
                    logger.info(f"✅ Enqueued document {doc.id} ({doc.filename})")
                    requeued_count += 1
                else:
                    logger.error(f"❌ Failed to enqueue document {doc.id}")
            
            logger.info(f"🎉 Requeued {requeued_count} documents")
            
    except Exception as e:
        logger.error(f"Error requeuing documents: {e}")
        import traceback
        traceback.print_exc()
    
    return requeued_count

async def main():
    """Main entry point for integrated worker"""
    logger.info("🚀 Starting integrated OCR worker...")
    
    # First, requeue any stuck documents
    await requeue_stuck_documents()
    
    # Start the worker manager
    manager = WorkerManager(num_workers=1)
    
    try:
        logger.info("🔄 Starting worker manager...")
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await manager.stop()
        logger.info("Worker stopped")

if __name__ == "__main__":
    asyncio.run(main())