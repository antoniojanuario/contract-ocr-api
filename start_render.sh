#!/bin/bash
# Script de inicialização para Render.com

echo "🚀 Starting Contract OCR API on Render..."

# Create uploads directory
mkdir -p uploads

# Initialize database
echo "📊 Initializing database..."
python -c "
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import engine, Base
from app.models.database import Document, Page, TextBlock, TaskRecord

print('Creating database tables...')
Base.metadata.create_all(bind=engine)
print('Database initialized successfully!')
"

# Start worker in background
echo "🔄 Starting OCR worker..."
python integrated_worker.py &

# Wait a moment for worker to start
sleep 2

# Start API server
echo "🌐 Starting API server on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
