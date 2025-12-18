#!/usr/bin/env python3
"""
Script para verificar o status da fila de tarefas
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_queue import get_task_queue
from app.db.base import get_db_session
from app.models.database import Document

async def check_queue_status():
    """Check the current status of the task queue and database"""
    print("🔍 Checking Queue and Database Status...")
    print(f"⏰ Current time: {datetime.now()}")
    
    try:
        # Check database for queued documents
        print("\n📊 Database Status:")
        with get_db_session() as db:
            total_docs = db.query(Document).count()
            queued_docs = db.query(Document).filter(Document.status == "queued").count()
            processing_docs = db.query(Document).filter(Document.status == "processing").count()
            completed_docs = db.query(Document).filter(Document.status == "completed").count()
            failed_docs = db.query(Document).filter(Document.status == "failed").count()
            
            print(f"  📄 Total documents: {total_docs}")
            print(f"  ⏳ Queued: {queued_docs}")
            print(f"  🔄 Processing: {processing_docs}")
            print(f"  ✅ Completed: {completed_docs}")
            print(f"  ❌ Failed: {failed_docs}")
            
            if queued_docs > 0:
                print("\n📋 Queued Documents:")
                queued_documents = db.query(Document).filter(Document.status == "queued").all()
                for doc in queued_documents:
                    print(f"  - {doc.id}: {doc.filename} (created: {doc.created_at})")
        
        # Check task queue
        print("\n🔄 Task Queue Status:")
        task_queue = await get_task_queue()
        print(f"  Queue type: {type(task_queue).__name__}")
        
        # Try to peek at queue (for InMemoryTaskQueue)
        if hasattr(task_queue, '_queue') and hasattr(task_queue._queue, 'qsize'):
            queue_size = task_queue._queue.qsize()
            print(f"  Queue size: {queue_size}")
        
        if hasattr(task_queue, '_tasks'):
            task_count = len(task_queue._tasks)
            print(f"  Total tasks in memory: {task_count}")
            
            if task_count > 0:
                print("  📋 Tasks in memory:")
                for task_id, task in task_queue._tasks.items():
                    print(f"    - {task_id}: {task.status} (doc: {task.document_id})")
        
        # Try to dequeue a task to see if there's anything waiting
        print("\n🧪 Testing queue dequeue...")
        task = await task_queue.dequeue()
        if task:
            print(f"  ✅ Found task: {task.id} for document {task.document_id}")
            # Put it back (this is just a test)
            await task_queue.enqueue(task)
        else:
            print("  ❌ No tasks available in queue")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_queue_status())