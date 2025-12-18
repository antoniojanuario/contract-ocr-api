#!/usr/bin/env python3
"""
Script to run the OCR task worker
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_worker import main

if __name__ == "__main__":
    asyncio.run(main())