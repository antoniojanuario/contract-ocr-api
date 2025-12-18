#!/usr/bin/env python3
"""
Script para testar o OCR engine diretamente
"""
import sys
import os
import asyncio

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ocr_engine import MultiBackendOCRService

async def test_ocr_engine():
    """Test OCR engine with a sample file"""
    print("🔍 Testing OCR Engine...")
    
    try:
        # Initialize OCR engine
        ocr_engine = MultiBackendOCRService()
        print("✅ OCR engine initialized")
        
        # Find a test file
        test_files = []
        uploads_dir = "uploads"
        
        if os.path.exists(uploads_dir):
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    if file.endswith('.pdf'):
                        test_files.append(os.path.join(root, file))
        
        if not test_files:
            print("❌ No PDF files found in uploads directory")
            return
        
        # Test with a real file (teste_original.pdf)
        test_file = None
        for file in test_files:
            if "teste_original.pdf" in file:
                test_file = file
                break
        
        if not test_file:
            test_file = test_files[0]
        print(f"🧪 Testing with file: {test_file}")
        
        # Check if file exists and has content
        if not os.path.exists(test_file):
            print(f"❌ File does not exist: {test_file}")
            return
        
        file_size = os.path.getsize(test_file)
        print(f"📊 File size: {file_size} bytes")
        
        if file_size == 0:
            print("❌ File is empty")
            return
        
        # Try OCR extraction
        print("🔄 Running OCR extraction...")
        pages_content = ocr_engine.extract_text_from_pdf(test_file)
        
        if pages_content:
            print(f"✅ OCR successful! Extracted {len(pages_content)} pages")
            
            for i, page in enumerate(pages_content):
                print(f"\n📄 Page {i+1}:")
                print(f"   📝 Raw text length: {len(page.raw_text)} characters")
                print(f"   🎯 Text blocks: {len(page.text_blocks)}")
                if page.raw_text:
                    preview = page.raw_text[:200].replace('\n', ' ')
                    print(f"   👀 Preview: {preview}...")
        else:
            print("❌ OCR failed - no content extracted")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ocr_engine())