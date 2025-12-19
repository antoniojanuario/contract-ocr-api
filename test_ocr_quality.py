#!/usr/bin/env python3
"""
Test script to evaluate OCR quality and performance
"""
import sys
import os
import time
from pathlib import Path

def test_ocr_engines():
    """Test available OCR engines and their capabilities"""
    print("🔍 Testing OCR Engine Quality and Performance\n")
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app.services.hybrid_ocr_engine import HybridOCREngine
        
        # Initialize engine
        print("📚 Initializing Hybrid OCR Engine...")
        engine = HybridOCREngine()
        
        # Check available engines
        available_engines = engine.get_available_engines()
        print(f"✅ Available engines: {available_engines}")
        
        # Test with a sample PDF if available
        test_pdf_path = "uploads/c5c9d405-e34e-42dc-8648-2df37824c213/teste_original.pdf"
        
        if os.path.exists(test_pdf_path):
            print(f"\n📄 Testing with sample PDF: {test_pdf_path}")
            
            # Measure performance
            start_time = time.time()
            
            try:
                pages = engine.extract_text_from_pdf(test_pdf_path)
                processing_time = time.time() - start_time
                
                print(f"⏱️  Processing time: {processing_time:.2f} seconds")
                print(f"📄 Pages processed: {len(pages)}")
                
                # Assess quality
                quality = engine.assess_quality(pages)
                print(f"\n📊 Quality Assessment:")
                for key, value in quality.items():
                    print(f"   {key}: {value}")
                
                # Show sample text from first page
                if pages and pages[0].raw_text:
                    sample_text = pages[0].raw_text[:200]
                    print(f"\n📝 Sample text (first 200 chars):")
                    print(f"   {sample_text}...")
                    
                    # Check if it looks like real text or placeholder
                    if "not available" in sample_text.lower() or "processing failed" in sample_text.lower():
                        print("⚠️  Warning: Appears to be placeholder text - OCR may not be working properly")
                    else:
                        print("✅ Real text extracted successfully")
                else:
                    print("❌ No text extracted from first page")
                
                return True, quality
                
            except Exception as e:
                print(f"❌ PDF processing failed: {e}")
                return False, None
        else:
            print(f"⚠️  Test PDF not found at: {test_pdf_path}")
            print("   Upload a PDF to test OCR functionality")
            
            # Test basic functionality without PDF
            quality = engine.assess_quality([])
            print(f"\n📊 Basic Quality Assessment: {quality}")
            return True, quality
            
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")
        return False, None

def test_ocr_libraries():
    """Test individual OCR library availability"""
    print("\n🔧 Testing OCR Library Availability:")
    
    # Test EasyOCR
    try:
        import easyocr
        print("✅ EasyOCR: Available")
        
        # Test initialization (this might take a while on first run)
        print("   Initializing EasyOCR reader...")
        reader = easyocr.Reader(['en'], gpu=False)  # CPU only for compatibility
        print("   ✅ EasyOCR reader initialized successfully")
        
    except ImportError:
        print("❌ EasyOCR: Not installed")
    except Exception as e:
        print(f"⚠️  EasyOCR: Available but initialization failed: {e}")
    
    # Test Tesseract
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract: Available (version {version})")
    except ImportError:
        print("❌ Tesseract: Not installed")
    except Exception as e:
        print(f"⚠️  Tesseract: Installation issue: {e}")
    
    # Test PDF libraries
    try:
        import pdfplumber
        print("✅ pdfplumber: Available")
    except ImportError:
        print("❌ pdfplumber: Not installed")
    
    try:
        import pypdf
        print("✅ pypdf: Available")
    except ImportError:
        print("❌ pypdf: Not installed")

def performance_recommendations(quality_data):
    """Provide performance recommendations based on test results"""
    if not quality_data:
        return
        
    print("\n💡 Performance Recommendations:")
    
    engines = quality_data.get('engines_available', [])
    
    if 'easyocr_ocr' in engines:
        print("✅ EasyOCR available - Good for scanned documents")
        print("   - Supports Portuguese and English")
        print("   - Good accuracy but slower processing")
        print("   - Recommended for image-based PDFs")
    
    if 'pdfplumber_native' in engines:
        print("✅ pdfplumber available - Excellent for native text PDFs")
        print("   - Very fast processing")
        print("   - High accuracy for text-based PDFs")
        print("   - Recommended as primary method")
    
    confidence = quality_data.get('overall_confidence', 0)
    if confidence > 0.9:
        print(f"🎯 Excellent confidence score: {confidence:.2f}")
    elif confidence > 0.7:
        print(f"👍 Good confidence score: {confidence:.2f}")
    elif confidence > 0.5:
        print(f"⚠️  Moderate confidence score: {confidence:.2f} - Consider image quality")
    else:
        print(f"❌ Low confidence score: {confidence:.2f} - Check OCR setup")
    
    native_pages = quality_data.get('native_text_pages', 0)
    ocr_pages = quality_data.get('ocr_pages', 0)
    
    if native_pages > 0 and ocr_pages == 0:
        print("📄 Document contains native text - Optimal performance")
    elif ocr_pages > 0 and native_pages == 0:
        print("🖼️  Document is image-based - OCR processing required")
    elif native_pages > 0 and ocr_pages > 0:
        print("📄🖼️  Mixed document - Hybrid processing used")

def main():
    """Main test function"""
    print("🚀 Contract OCR Quality and Performance Test\n")
    
    # Test OCR libraries
    test_ocr_libraries()
    
    # Test OCR engines
    success, quality = test_ocr_engines()
    
    if success:
        print("\n✅ OCR Engine Test Completed Successfully")
        performance_recommendations(quality)
    else:
        print("\n❌ OCR Engine Test Failed")
        print("💡 Recommendations:")
        print("   - Install EasyOCR: pip install easyocr")
        print("   - Install pdfplumber: pip install pdfplumber")
        print("   - Check PDF file availability")
    
    print("\n🎯 Next Steps:")
    print("   - Upload test PDFs to verify OCR quality")
    print("   - Monitor processing times for performance optimization")
    print("   - Adjust confidence thresholds based on requirements")

if __name__ == "__main__":
    main()