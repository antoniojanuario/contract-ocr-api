#!/bin/bash
# Script de inicialização para Render.com

echo "🚀 Starting Contract OCR API on Render..."

# Install dependencies if not already installed
if [ ! -f ".deps_installed" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements-render.txt
    touch .deps_installed
fi

# Create uploads directory
mkdir -p uploads

# Initialize database
echo "📊 Initializing database..."
python -c "
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.db.base import engine, Base
    from app.models.database import Document, Page, TextBlock, TaskRecord

    print('Creating database tables...')
    Base.metadata.create_all(bind=engine)
    print('Database initialized successfully!')
except Exception as e:
    print(f'Database initialization failed: {e}')
    print('Continuing with startup...')
"

# Start worker in background
echo "🔄 Starting OCR worker..."
python integrated_worker.py &

# Wait a moment for worker to start
sleep 2

# Start API server
echo "🌐 Starting API server on port $PORT..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT
