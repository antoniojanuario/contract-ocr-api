#!/usr/bin/env python3
"""
Script para verificar documentos completados
"""
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import get_db_session
from app.models.database import Document

def check_completed_documents():
    """Check completed documents"""
    print("🔍 Checking completed documents...")
    
    try:
        with get_db_session() as db:
            # Get completed documents
            completed_docs = db.query(Document).filter(Document.status == "completed").all()
            
            print(f"✅ Found {len(completed_docs)} completed documents:")
            
            for doc in completed_docs:
                print(f"\n📄 Document: {doc.id}")
                print(f"   📁 Filename: {doc.filename}")
                print(f"   📊 Status: {doc.status}")
                print(f"   📈 Progress: {doc.progress}%")
                print(f"   📄 Pages: {doc.page_count}")
                print(f"   ⏱️ Processing time: {doc.processing_time}s")
                print(f"   🎯 OCR confidence: {doc.ocr_confidence}")
                print(f"   📅 Created: {doc.created_at}")
                print(f"   🔄 Updated: {doc.updated_at}")
                
            # Get failed documents
            failed_docs = db.query(Document).filter(Document.status == "failed").all()
            
            print(f"\n❌ Found {len(failed_docs)} failed documents:")
            
            for doc in failed_docs:
                print(f"\n📄 Document: {doc.id}")
                print(f"   📁 Filename: {doc.filename}")
                print(f"   ❌ Error: {doc.error_message}")
                print(f"   📅 Created: {doc.created_at}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_completed_documents()