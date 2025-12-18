#!/usr/bin/env python3
"""
Database initialization script for deployment
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.db.init_db import init_database
from app.core.logging import setup_logging

logger = setup_logging()


async def main():
    """Initialize database for deployment"""
    try:
        logger.info(f"Initializing database for environment: {settings.ENVIRONMENT}")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        # Initialize database
        await init_database()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())