#!/usr/bin/env python3
"""
Script para verificar quais documentos têm páginas salvas no banco
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import get_db_session
from app.models.database import Document, Page

def check_pages():
    """Check which documents have pages saved"""
    print("🔍 Checking documents with pages...")
    
    try:
        with get_db_session() as db:
            # Get all completed documents
            completed_docs = db.query(Document).filter(Document.status == "completed").all()
            
            print(f"📄 Found {len(completed_docs)} completed documents")
            
            for doc in completed_docs:
                # Count pages for this document
                page_count = db.query(Page).filter(Page.document_id == doc.id).count()
                
                if page_count > 0:
                    print(f"\n✅ Document {doc.id}:")
                    print(f"   📁 Filename: {doc.filename}")
                    print(f"   📄 Pages in DB: {page_count}")
                    print(f"   📅 Updated: {doc.updated_at}")
                    
                    # Show first page preview
                    first_page = db.query(Page).filter(Page.document_id == doc.id).first()
                    if first_page and first_page.raw_text:
                        preview = first_page.raw_text[:200].replace('\n', ' ')
                        print(f"   👀 Preview: {preview}...")
                else:
                    print(f"❌ Document {doc.id} ({doc.filename}) - No pages saved")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_pages()