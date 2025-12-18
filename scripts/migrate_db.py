#!/usr/bin/env python3
"""
Database migration script for deployment
"""
import subprocess
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import setup_logging

logger = setup_logging()


def run_migrations():
    """Run Alembic migrations"""
    try:
        logger.info(f"Running database migrations for environment: {settings.ENVIRONMENT}")
        logger.info(f"Database URL: {settings.DATABASE_URL}")
        
        # Run Alembic upgrade
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
            logger.info(f"Migration output: {result.stdout}")
        else:
            logger.error(f"Migration failed: {result.stderr}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()