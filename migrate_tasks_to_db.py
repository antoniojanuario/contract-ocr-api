#!/usr/bin/env python3
"""
Script para migrar tarefas da fila in-memory para o banco de dados
"""
import asyncio
import sys
import os
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_queue import get_task_queue, DatabaseTaskQueue
from app.db.base import get_db_session
from app.models.database import Document

async def migrate_tasks():
    """Migrate existing queued documents to database tasks"""
    print("🔄 Migrating tasks to database...")
    
    try:
        # Get database queue
        db_queue = DatabaseTaskQueue()
        
        # Get all queued documents from database
        with get_db_session() as db:
            queued_docs = db.query(Document).filter(Document.status == "queued").all()
            
            print(f"📋 Found {len(queued_docs)} queued documents")
            
            migrated_count = 0
            
            for doc in queued_docs:
                # Check if file exists
                from app.services.file_storage import FileStorageService
                file_storage = FileStorageService()
                
                file_path = file_storage._generate_file_path(doc.id, doc.filename)
                full_path = os.path.join(file_storage.backend.base_path, file_path)
                
                if os.path.exists(full_path):
                    # Create task for this document
                    from app.services.task_worker import create_ocr_task
                    
                    task = await create_ocr_task(
                        document_id=doc.id,
                        filename=doc.filename,
                        file_path=full_path
                    )
                    
                    # Enqueue in database
                    success = await db_queue.enqueue(task)
                    
                    if success:
                        print(f"✅ Migrated task for document {doc.id} ({doc.filename})")
                        migrated_count += 1
                    else:
                        print(f"❌ Failed to migrate task for document {doc.id}")
                else:
                    print(f"⚠️ File not found for document {doc.id}: {full_path}")
            
            print(f"🎉 Successfully migrated {migrated_count} tasks to database")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_tasks())