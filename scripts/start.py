#!/usr/bin/env python3
"""
Optimized startup script for deployment on free platforms
"""
import asyncio
import os
import sys
import signal
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.monitoring import resource_monitor

logger = setup_logging()


class GracefulShutdown:
    """Handle graceful shutdown"""
    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)
    
    def _exit_gracefully(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown = True


async def startup_checks():
    """Perform startup checks and initialization"""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Check database connectivity
    try:
        from app.db.init_db import check_database_connection
        await check_database_connection()
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        if settings.ENVIRONMENT != "local":
            sys.exit(1)
    
    # Check Redis connectivity if enabled
    if settings.USE_REDIS:
        try:
            import redis.asyncio as redis
            r = redis.from_url(settings.REDIS_URL)
            await r.ping()
            logger.info("Redis connection verified")
            await r.close()
        except Exception as e:
            logger.warning(f"Redis connection failed, falling back to in-memory queue: {e}")
    
    # Log resource information
    import psutil
    memory_gb = psutil.virtual_memory().total / (1024**3)
    cpu_count = psutil.cpu_count()
    logger.info(f"System resources: {cpu_count} CPUs, {memory_gb:.1f}GB RAM")
    logger.info(f"Optimized settings: max_file_size={settings.optimized_max_file_size/1024/1024:.0f}MB, "
               f"ocr_timeout={settings.optimized_ocr_timeout}s")


async def main():
    """Main startup function"""
    shutdown_handler = GracefulShutdown()
    
    try:
        # Perform startup checks
        await startup_checks()
        
        # Start resource monitoring if enabled
        if settings.ENABLE_METRICS:
            monitoring_task = asyncio.create_task(
                resource_monitor.start_monitoring(interval=60)
            )
            logger.info("Resource monitoring started")
        
        # Keep the script running
        while not shutdown_handler.shutdown:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)
    finally:
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())