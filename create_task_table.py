#!/usr/bin/env python3
"""
Script para criar a tabela task_records
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import engine, Base
from app.models.database import TaskRecord

def create_task_table():
    """Create the task_records table"""
    print("🔧 Creating task_records table...")
    
    try:
        # Create the table
        TaskRecord.__table__.create(engine, checkfirst=True)
        print("✅ task_records table created successfully")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")

if __name__ == "__main__":
    create_task_table()