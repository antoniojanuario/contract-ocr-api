"""
Task queue service for asynchronous document processing
"""
import asyncio
import json
import logging
import os
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
import threading

from app.core.config import settings

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class Task:
    """Task data structure"""
    id: str
    document_id: str
    task_type: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    progress: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary"""
        # Convert ISO strings back to datetime objects
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        return cls(**data)


class TaskQueue(ABC):
    """Abstract base class for task queue implementations"""
    
    @abstractmethod
    async def enqueue(self, task: Task) -> bool:
        """Add task to queue"""
        pass
    
    @abstractmethod
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue"""
        pass
    
    @abstractmethod
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                progress: int = None, error_message: str = None) -> bool:
        """Update task status"""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        pass
    
    @abstractmethod
    async def get_tasks_by_document(self, document_id: str) -> List[Task]:
        """Get all tasks for a document"""
        pass
    
    @abstractmethod
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed tasks"""
        pass


class InMemoryTaskQueue(TaskQueue):
    """In-memory task queue implementation with file persistence (fallback)"""
    
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._queue_file = "task_queue.json"
        self._load_from_file()
        logger.info("Initialized in-memory task queue with file persistence")
    
    def _load_from_file(self):
        """Load tasks from file"""
        try:
            if os.path.exists(self._queue_file):
                with open(self._queue_file, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = Task.from_dict(task_data)
                        self._tasks[task.id] = task
                    
                    # Load pending queue
                    for task_id in data.get('pending_queue', []):
                        if task_id in self._tasks and self._tasks[task_id].status == TaskStatus.PENDING:
                            self._queue.put_nowait(task_id)
                    
                logger.info(f"Loaded {len(self._tasks)} tasks from file")
        except Exception as e:
            logger.error(f"Failed to load tasks from file: {e}")
    
    def _save_to_file(self):
        """Save tasks to file"""
        try:
            data = {
                'tasks': [task.to_dict() for task in self._tasks.values()],
                'pending_queue': []
            }
            
            # Add pending tasks to queue data
            temp_queue = []
            while not self._queue.empty():
                try:
                    task_id = self._queue.get_nowait()
                    temp_queue.append(task_id)
                    data['pending_queue'].append(task_id)
                except:
                    break
            
            # Put tasks back in queue
            for task_id in temp_queue:
                self._queue.put_nowait(task_id)
            
            with open(self._queue_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tasks to file: {e}")
    
    async def enqueue(self, task: Task) -> bool:
        """Add task to queue"""
        try:
            async with self._lock:
                self._tasks[task.id] = task
                await self._queue.put(task.id)
                self._save_to_file()
            logger.info(f"Enqueued task {task.id} for document {task.document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue"""
        try:
            # Wait for task with timeout
            task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            async with self._lock:
                task = self._tasks.get(task_id)
                if task and task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow()
                    return task
            return None
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                progress: int = None, error_message: str = None) -> bool:
        """Update task status"""
        try:
            async with self._lock:
                task = self._tasks.get(task_id)
                if not task:
                    return False
                
                task.status = status
                if progress is not None:
                    task.progress = progress
                if error_message:
                    task.error_message = error_message
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task.completed_at = datetime.utcnow()
                
            logger.info(f"Updated task {task_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        async with self._lock:
            return self._tasks.get(task_id)
    
    async def get_tasks_by_document(self, document_id: str) -> List[Task]:
        """Get all tasks for a document"""
        async with self._lock:
            return [task for task in self._tasks.values() 
                   if task.document_id == document_id]
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed tasks"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        async with self._lock:
            tasks_to_remove = []
            for task_id, task in self._tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and
                    task.completed_at and task.completed_at < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self._tasks[task_id]
                cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} old tasks")
        return cleaned_count


class RedisTaskQueue(TaskQueue):
    """Redis-based task queue implementation"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
        self._initialized = False
        logger.info(f"Initializing Redis task queue with URL: {redis_url}")
    
    async def _ensure_redis(self):
        """Ensure Redis connection is established"""
        if not self._initialized:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                # Test connection
                await self._redis.ping()
                self._initialized = True
                logger.info("Redis task queue initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis: {e}")
                raise
    
    async def enqueue(self, task: Task) -> bool:
        """Add task to queue"""
        try:
            await self._ensure_redis()
            
            # Store task data
            task_data = json.dumps(task.to_dict())
            await self._redis.hset("tasks", task.id, task_data)
            
            # Add to processing queue
            await self._redis.lpush("task_queue", task.id)
            
            # Add to document index
            await self._redis.sadd(f"doc_tasks:{task.document_id}", task.id)
            
            logger.info(f"Enqueued task {task.id} for document {task.document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False
    
    async def dequeue(self) -> Optional[Task]:
        """Get next task from queue"""
        try:
            await self._ensure_redis()
            
            # Get task ID from queue (blocking with timeout)
            result = await self._redis.brpop("task_queue", timeout=1)
            if not result:
                return None
            
            _, task_id = result
            
            # Get task data
            task_data = await self._redis.hget("tasks", task_id)
            if not task_data:
                return None
            
            task = Task.from_dict(json.loads(task_data))
            
            # Update status to processing
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.utcnow()
                await self._update_task_data(task)
                return task
            
            return None
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None
    
    async def _update_task_data(self, task: Task) -> bool:
        """Update task data in Redis"""
        try:
            task_data = json.dumps(task.to_dict())
            await self._redis.hset("tasks", task.id, task_data)
            return True
        except Exception as e:
            logger.error(f"Failed to update task data {task.id}: {e}")
            return False
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                progress: int = None, error_message: str = None) -> bool:
        """Update task status"""
        try:
            await self._ensure_redis()
            
            # Get current task data
            task_data = await self._redis.hget("tasks", task_id)
            if not task_data:
                return False
            
            task = Task.from_dict(json.loads(task_data))
            
            # Update task
            task.status = status
            if progress is not None:
                task.progress = progress
            if error_message:
                task.error_message = error_message
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.utcnow()
            
            # Save updated task
            await self._update_task_data(task)
            
            logger.info(f"Updated task {task_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        try:
            await self._ensure_redis()
            task_data = await self._redis.hget("tasks", task_id)
            if task_data:
                return Task.from_dict(json.loads(task_data))
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def get_tasks_by_document(self, document_id: str) -> List[Task]:
        """Get all tasks for a document"""
        try:
            await self._ensure_redis()
            task_ids = await self._redis.smembers(f"doc_tasks:{document_id}")
            tasks = []
            
            for task_id in task_ids:
                task_data = await self._redis.hget("tasks", task_id)
                if task_data:
                    tasks.append(Task.from_dict(json.loads(task_data)))
            
            return tasks
        except Exception as e:
            logger.error(f"Failed to get tasks for document {document_id}: {e}")
            return []
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed tasks"""
        try:
            await self._ensure_redis()
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            cleaned_count = 0
            
            # Get all task IDs
            task_ids = await self._redis.hkeys("tasks")
            
            for task_id in task_ids:
                task_data = await self._redis.hget("tasks", task_id)
                if task_data:
                    task = Task.from_dict(json.loads(task_data))
                    if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and
                        task.completed_at and task.completed_at < cutoff_time):
                        
                        # Remove from tasks hash
                        await self._redis.hdel("tasks", task_id)
                        
                        # Remove from document index
                        await self._redis.srem(f"doc_tasks:{task.document_id}", task_id)
                        
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old tasks")
            return cleaned_count
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0


class DatabaseTaskQueue(TaskQueue):
    """Database-based task queue implementation (most reliable)"""
    
    def __init__(self):
        logger.info("Initialized database task queue")
    
    async def enqueue(self, task: Task) -> bool:
        """Add task to database queue"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            with get_db_session() as db:
                # Create task record
                task_record = TaskRecord(
                    id=task.id,
                    document_id=task.document_id,
                    task_type=task.task_type,
                    status=task.status.value,
                    payload=json.dumps(task.payload),
                    created_at=task.created_at,
                    retry_count=task.retry_count,
                    max_retries=task.max_retries,
                    progress=task.progress
                )
                
                db.add(task_record)
                db.commit()
                
            logger.info(f"Enqueued task {task.id} for document {task.document_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue task {task.id}: {e}")
            return False
    
    async def dequeue(self) -> Optional[Task]:
        """Get next pending task from database"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            with get_db_session() as db:
                # Get oldest pending task
                task_record = db.query(TaskRecord).filter(
                    TaskRecord.status == TaskStatus.PENDING.value
                ).order_by(TaskRecord.created_at).first()
                
                if not task_record:
                    return None
                
                # Convert to Task object
                task = Task(
                    id=task_record.id,
                    document_id=task_record.document_id,
                    task_type=task_record.task_type,
                    payload=json.loads(task_record.payload),
                    status=TaskStatus(task_record.status),
                    created_at=task_record.created_at,
                    retry_count=task_record.retry_count,
                    max_retries=task_record.max_retries,
                    progress=task_record.progress
                )
                
                # Mark as processing
                task_record.status = TaskStatus.PROCESSING.value
                task_record.started_at = datetime.utcnow()
                db.commit()
                
                task.status = TaskStatus.PROCESSING
                task.started_at = task_record.started_at
                
                return task
                
        except Exception as e:
            logger.error(f"Failed to dequeue task: {e}")
            return None
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                                progress: int = None, error_message: str = None) -> bool:
        """Update task status in database"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            with get_db_session() as db:
                task_record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
                
                if not task_record:
                    return False
                
                task_record.status = status.value
                if progress is not None:
                    task_record.progress = progress
                if error_message:
                    task_record.error_message = error_message
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    task_record.completed_at = datetime.utcnow()
                
                db.commit()
                
            logger.info(f"Updated task {task_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID from database"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            with get_db_session() as db:
                task_record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
                
                if not task_record:
                    return None
                
                return Task(
                    id=task_record.id,
                    document_id=task_record.document_id,
                    task_type=task_record.task_type,
                    payload=json.loads(task_record.payload),
                    status=TaskStatus(task_record.status),
                    created_at=task_record.created_at,
                    started_at=task_record.started_at,
                    completed_at=task_record.completed_at,
                    retry_count=task_record.retry_count,
                    max_retries=task_record.max_retries,
                    progress=task_record.progress,
                    error_message=task_record.error_message
                )
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None
    
    async def get_tasks_by_document(self, document_id: str) -> List[Task]:
        """Get all tasks for a document from database"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            tasks = []
            with get_db_session() as db:
                task_records = db.query(TaskRecord).filter(
                    TaskRecord.document_id == document_id
                ).all()
                
                for record in task_records:
                    task = Task(
                        id=record.id,
                        document_id=record.document_id,
                        task_type=record.task_type,
                        payload=json.loads(record.payload),
                        status=TaskStatus(record.status),
                        created_at=record.created_at,
                        started_at=record.started_at,
                        completed_at=record.completed_at,
                        retry_count=record.retry_count,
                        max_retries=record.max_retries,
                        progress=record.progress,
                        error_message=record.error_message
                    )
                    tasks.append(task)
            
            return tasks
        except Exception as e:
            logger.error(f"Failed to get tasks for document {document_id}: {e}")
            return []
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed tasks from database"""
        try:
            from app.db.base import get_db_session
            from app.models.database import TaskRecord
            
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            with get_db_session() as db:
                deleted_count = db.query(TaskRecord).filter(
                    TaskRecord.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]),
                    TaskRecord.completed_at < cutoff_time
                ).delete()
                
                db.commit()
            
            logger.info(f"Cleaned up {deleted_count} old tasks")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}")
            return 0


class TaskQueueManager:
    """Task queue manager with database-first approach"""
    
    def __init__(self):
        self._queue: Optional[TaskQueue] = None
        self._initialized = False
    
    async def initialize(self) -> TaskQueue:
        """Initialize task queue - always use database queue for reliability"""
        if self._initialized:
            return self._queue
        
        # Always use database queue for maximum reliability
        self._queue = DatabaseTaskQueue()
        logger.info("Using database task queue")
        
        self._initialized = True
        return self._queue
    
    async def get_queue(self) -> TaskQueue:
        """Get initialized task queue"""
        if not self._initialized:
            await self.initialize()
        return self._queue


# Global task queue manager instance
task_queue_manager = TaskQueueManager()


async def get_task_queue() -> TaskQueue:
    """Dependency to get task queue instance"""
    return await task_queue_manager.get_queue()