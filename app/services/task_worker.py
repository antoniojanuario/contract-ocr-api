"""
Background worker for processing OCR tasks
"""
import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import threading

from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.base import get_db_session
from app.models.database import Document
from app.models.schemas import ProcessingStatus
from app.services.task_queue import (
    TaskQueue, Task, TaskStatus, get_task_queue
)
from app.services.ocr_engine import MultiBackendOCRService
from app.services.text_processor import TextNormalizer
from app.services.page_organizer import PageOrganizer
from app.services.file_storage import FileStorageService
from app.services.webhook_service import get_webhook_service

logger = logging.getLogger(__name__)


class TaskProcessor:
    """Processes individual OCR tasks"""
    
    def __init__(self):
        self.ocr_engine = MultiBackendOCRService()
        self.text_processor = TextNormalizer()
        self.page_organizer = PageOrganizer()
        self.file_storage = FileStorageService()
        self.webhook_service = get_webhook_service()
        self._executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent OCR operations
    
    async def process_task(self, task: Task, task_queue: TaskQueue) -> bool:
        """Process a single OCR task"""
        logger.info(f"Processing task {task.id} for document {task.document_id}")
        
        try:
            # Update database status
            await self._update_document_status(
                task.document_id, 
                ProcessingStatus.PROCESSING, 
                progress=10
            )
            
            # Update task status
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.PROCESSING, 
                progress=10
            )
            
            # Get file path from task payload
            file_path = task.payload.get("file_path")
            if not file_path:
                raise Exception("File path not found in task payload")
            
            # Verify file exists
            if not os.path.exists(file_path):
                raise Exception(f"Document file not found: {file_path}")
            
            # Progress: 20%
            await self._update_progress(task, task_queue, 20, "Starting OCR extraction")
            
            # Run OCR extraction (CPU intensive, run in thread pool)
            loop = asyncio.get_event_loop()
            pages_content = await loop.run_in_executor(
                self._executor,
                self.ocr_engine.extract_text_from_pdf,
                file_path
            )
            
            if not pages_content:
                raise Exception("No content extracted from document")
            
            # Progress: 50%
            await self._update_progress(task, task_queue, 50, "OCR extraction completed")
            
            # Process text for each page
            processed_pages = []
            total_pages = len(pages_content)
            
            for i, page_content in enumerate(pages_content):
                # Normalize text
                normalization_result = await loop.run_in_executor(
                    self._executor,
                    self.text_processor.normalize_text,
                    page_content.raw_text
                )
                
                # Extract normalized text from result
                if hasattr(normalization_result, 'normalized_text'):
                    normalized_text = normalization_result.normalized_text
                else:
                    # Fallback if it's already a string
                    normalized_text = str(normalization_result)
                
                # Update page content
                page_content.normalized_text = normalized_text
                processed_pages.append(page_content)
                
                # Update progress
                progress = 50 + int((i + 1) / total_pages * 30)  # 50% to 80%
                await self._update_progress(
                    task, task_queue, progress, 
                    f"Processing page {i + 1} of {total_pages}"
                )
            
            # Progress: 80%
            await self._update_progress(task, task_queue, 80, "Organizing content")
            
            # Organize pages and save to database
            await self._save_pages_to_database(
                task.document_id, 
                processed_pages
            )
            
            # Progress: 90%
            await self._update_progress(task, task_queue, 90, "Finalizing results")
            
            # Calculate overall confidence
            total_confidence = sum(page.text_blocks[0].confidence if page.text_blocks else 0.0 
                                 for page in processed_pages)
            avg_confidence = total_confidence / len(processed_pages) if processed_pages else 0.0
            
            # Update document as completed
            processing_time = time.time() - task.created_at.timestamp()
            await self._update_document_completion(
                task.document_id,
                processing_time,
                avg_confidence,
                len(processed_pages)
            )
            
            # Complete task
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.COMPLETED, 
                progress=100
            )
            
            # Send webhook notification for completion
            await self._send_completion_webhook(task.document_id, {
                "status": "completed",
                "processing_time": processing_time,
                "page_count": len(processed_pages),
                "ocr_confidence": avg_confidence,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Successfully completed task {task.id}")
            return True
            
        except Exception as e:
            error_msg = f"Task processing failed: {str(e)}"
            logger.error(f"Task {task.id} failed: {error_msg}")
            
            # Update task as failed
            await task_queue.update_task_status(
                task.id, 
                TaskStatus.FAILED, 
                error_message=error_msg
            )
            
            # Update document as failed
            await self._update_document_status(
                task.document_id, 
                ProcessingStatus.FAILED, 
                error_message=error_msg
            )
            
            # Send webhook notification for failure
            await self._send_failure_webhook(task.document_id, {
                "status": "failed",
                "error_message": error_msg,
                "failed_at": datetime.utcnow().isoformat()
            })
            
            return False
    
    async def _update_progress(self, task: Task, task_queue: TaskQueue, 
                              progress: int, message: str):
        """Update task and document progress"""
        await task_queue.update_task_status(task.id, TaskStatus.PROCESSING, progress=progress)
        await self._update_document_status(task.document_id, ProcessingStatus.PROCESSING, progress=progress)
        logger.info(f"Task {task.id}: {message} ({progress}%)")
    
    async def _update_document_status(self, document_id: str, status: ProcessingStatus, 
                                     progress: int = None, error_message: str = None):
        """Update document status in database"""
        try:
            with get_db_session() as db:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = status.value
                    document.updated_at = datetime.utcnow()
                    if progress is not None:
                        document.progress = progress
                    if error_message:
                        document.error_message = error_message
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update document {document_id} status: {e}")
    
    async def _save_pages_to_database(self, document_id: str, pages_content: list):
        """Save pages content to database"""
        try:
            from app.models.database import Page, TextBlock
            
            with get_db_session() as db:
                for page_content in pages_content:
                    # Create page record
                    page = Page(
                        document_id=document_id,
                        page_number=page_content.page_number,
                        raw_text=page_content.raw_text,
                        normalized_text=page_content.normalized_text,
                        confidence=sum(block.confidence for block in page_content.text_blocks) / len(page_content.text_blocks) if page_content.text_blocks else 0.0,
                        page_metadata={
                            "tables": page_content.tables,
                            "images": page_content.images
                        }
                    )
                    db.add(page)
                    db.flush()  # Get the page ID
                    
                    # Create text block records
                    for text_block in page_content.text_blocks:
                        block = TextBlock(
                            page_id=page.id,
                            text=text_block.text,
                            confidence=text_block.confidence,
                            x=text_block.bounding_box.x,
                            y=text_block.bounding_box.y,
                            width=text_block.bounding_box.width,
                            height=text_block.bounding_box.height,
                            font_size=text_block.font_size,
                            is_title=text_block.is_title
                        )
                        db.add(block)
                
                db.commit()
                logger.info(f"Saved {len(pages_content)} pages to database for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to save pages to database for document {document_id}: {e}")
    
    async def _update_document_completion(self, document_id: str, processing_time: float, 
                                         confidence: float, page_count: int):
        """Update document with completion data"""
        try:
            with get_db_session() as db:
                document = db.query(Document).filter(Document.id == document_id).first()
                if document:
                    document.status = ProcessingStatus.COMPLETED.value
                    document.progress = 100
                    document.processing_time = processing_time
                    document.ocr_confidence = confidence
                    document.page_count = page_count
                    document.updated_at = datetime.utcnow()
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update document {document_id} completion: {e}")
    
    async def _send_completion_webhook(self, document_id: str, completion_data: dict):
        """Send webhook notification for document completion"""
        try:
            await self.webhook_service.notify_document_completed(document_id, completion_data)
        except Exception as e:
            logger.error(f"Failed to send completion webhook for document {document_id}: {e}")
    
    async def _send_failure_webhook(self, document_id: str, failure_data: dict):
        """Send webhook notification for document failure"""
        try:
            await self.webhook_service.notify_document_failed(document_id, failure_data)
        except Exception as e:
            logger.error(f"Failed to send failure webhook for document {document_id}: {e}")


class TaskWorker:
    """Background worker that processes tasks from the queue"""
    
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.processor = TaskProcessor()
        self.running = False
        self.task_queue: Optional[TaskQueue] = None
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start the worker"""
        logger.info(f"Starting task worker {self.worker_id}")
        
        # Initialize task queue
        self.task_queue = await get_task_queue()
        
        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()
        
        self.running = True
        
        # Main processing loop
        while self.running:
            try:
                # Get next task from queue
                task = await self.task_queue.dequeue()
                
                if task:
                    logger.info(f"Worker {self.worker_id} got task {task.id}")
                    
                    # Process task with retry logic
                    success = await self._process_task_with_retry(task)
                    
                    if success:
                        logger.info(f"Worker {self.worker_id} completed task {task.id}")
                    else:
                        logger.error(f"Worker {self.worker_id} failed to process task {task.id}")
                
                else:
                    # No tasks available, wait a bit
                    await asyncio.sleep(1)
                
                # Check for shutdown signal
                if self._shutdown_event.is_set():
                    break
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info(f"Task worker {self.worker_id} stopped")
    
    async def _process_task_with_retry(self, task: Task) -> bool:
        """Process task with retry logic"""
        max_retries = task.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retrying task {task.id}, attempt {attempt + 1}/{max_retries + 1}")
                    await self.task_queue.update_task_status(
                        task.id, 
                        TaskStatus.RETRYING,
                        progress=0
                    )
                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(min(2 ** attempt, 60))
                
                # Process the task
                success = await self.processor.process_task(task, self.task_queue)
                
                if success:
                    return True
                
                # If not successful and we have retries left, continue loop
                if attempt < max_retries:
                    task.retry_count = attempt + 1
                    continue
                else:
                    # Max retries reached
                    logger.error(f"Task {task.id} failed after {max_retries + 1} attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"Task {task.id} attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries:
                    task.retry_count = attempt + 1
                    continue
                else:
                    # Max retries reached, mark as failed
                    await self.task_queue.update_task_status(
                        task.id, 
                        TaskStatus.FAILED,
                        error_message=f"Failed after {max_retries + 1} attempts: {str(e)}"
                    )
                    return False
        
        return False
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Worker {self.worker_id} received shutdown signal")
            self.running = False
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"Stopping task worker {self.worker_id}")
        self.running = False
        self._shutdown_event.set()


class WorkerManager:
    """Manages multiple worker processes"""
    
    def __init__(self, num_workers: int = 1):
        self.num_workers = num_workers
        self.workers: Dict[str, TaskWorker] = {}
        self.running = False
    
    async def start(self):
        """Start all workers"""
        logger.info(f"Starting {self.num_workers} workers")
        self.running = True
        
        # Create and start workers
        tasks = []
        for i in range(self.num_workers):
            worker_id = f"worker-{i+1}"
            worker = TaskWorker(worker_id)
            self.workers[worker_id] = worker
            tasks.append(asyncio.create_task(worker.start()))
        
        # Wait for all workers to complete
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Worker manager error: {e}")
        finally:
            self.running = False
    
    async def stop(self):
        """Stop all workers"""
        logger.info("Stopping all workers")
        self.running = False
        
        # Stop all workers
        for worker in self.workers.values():
            await worker.stop()
        
        self.workers.clear()


# Utility functions for task creation

async def create_ocr_task(document_id: str, filename: str, file_path: str) -> Task:
    """Create an OCR processing task"""
    task = Task(
        id=f"ocr_{document_id}_{int(time.time())}",
        document_id=document_id,
        task_type="ocr_processing",
        payload={
            "filename": filename,
            "file_path": file_path,
            "created_at": datetime.utcnow().isoformat()
        },
        max_retries=3
    )
    return task


async def enqueue_document_processing(document_id: str, filename: str, file_path: str) -> bool:
    """Enqueue a document for OCR processing"""
    try:
        task_queue = await get_task_queue()
        task = await create_ocr_task(document_id, filename, file_path)
        return await task_queue.enqueue(task)
    except Exception as e:
        logger.error(f"Failed to enqueue document {document_id}: {e}")
        return False


# Main entry point for running worker
async def main():
    """Main entry point for running the worker process"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OCR Task Worker")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start worker manager
    manager = WorkerManager(num_workers=args.workers)
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await manager.stop()


if __name__ == "__main__":
    asyncio.run(main())