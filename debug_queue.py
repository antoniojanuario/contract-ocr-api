#!/usr/bin/env python3
"""
Script para debugar o sistema de filas
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_queue import get_task_queue
from app.services.task_worker import enqueue_document_processing

async def debug_queue():
    """Debug the task queue system"""
    print("🔍 Debugging Task Queue System...")
    
    try:
        # Get task queue
        task_queue = await get_task_queue()
        print(f"✅ Task queue initialized: {type(task_queue).__name__}")
        
        # Check if there are any existing tasks
        print("\n📋 Checking existing tasks...")
        
        # Try to create a test task
        print("\n🧪 Creating test task...")
        success = await enqueue_document_processing(
            document_id="test-123",
            filename="test.pdf", 
            file_path="/fake/path/test.pdf"
        )
        
        if success:
            print("✅ Test task enqueued successfully")
        else:
            print("❌ Failed to enqueue test task")
        
        # Try to dequeue a task
        print("\n📤 Trying to dequeue task...")
        task = await task_queue.dequeue()
        
        if task:
            print(f"✅ Dequeued task: {task.id} for document {task.document_id}")
        else:
            print("❌ No tasks in queue")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_queue())