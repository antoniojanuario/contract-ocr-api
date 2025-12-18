#!/usr/bin/env python3
"""
Script para reprocessar documentos que ficaram presos em "queued"
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_worker import enqueue_document_processing
from app.services.file_storage import FileStorageService
from app.db.base import get_db_session
from app.models.database import Document

async def requeue_stuck_documents():
    """Requeue documents that are stuck in queued status"""
    print("🔄 Requeuing stuck documents...")
    
    file_storage = FileStorageService()
    
    try:
        with get_db_session() as db:
            # Get all queued documents
            queued_docs = db.query(Document).filter(Document.status == "queued").all()
            
            print(f"📋 Found {len(queued_docs)} documents in queued status")
            
            for doc in queued_docs:
                print(f"\n🔄 Processing document: {doc.id} ({doc.filename})")
                
                # Generate file path
                file_path = file_storage._generate_file_path(doc.id, doc.filename)
                full_path = os.path.join(file_storage.backend.base_path, file_path)
                
                if not os.path.exists(full_path):
                    print(f"  ❌ File does not exist: {full_path}")
                    continue
                
                # Enqueue for processing
                success = await enqueue_document_processing(
                    document_id=doc.id,
                    filename=doc.filename,
                    file_path=full_path
                )
                
                if success:
                    print(f"  ✅ Successfully enqueued document {doc.id}")
                else:
                    print(f"  ❌ Failed to enqueue document {doc.id}")
            
            print(f"\n🎉 Finished requeuing {len(queued_docs)} documents")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(requeue_stuck_documents())