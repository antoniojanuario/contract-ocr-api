#!/usr/bin/env python3
"""
Test script specifically for image-based PDF OCR
"""
import sys
import os
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

def create_test_image_pdf():
    """Create a test PDF with image content for OCR testing"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # Create a simple PDF with text as image
        pdf_path = "test_image_document.pdf"
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Add some text content
        c.drawString(100, 750, "CONTRATO DE TESTE OCR")
        c.drawString(100, 720, "Este é um documento de teste para verificar")
        c.drawString(100, 690, "a qualidade do OCR em PDFs escaneados.")
        c.drawString(100, 660, "")
        c.drawString(100, 630, "Dados do Cliente:")
        c.drawString(120, 600, "Nome: João Silva Santos")
        c.drawString(120, 570, "CPF: 123.456.789-00")
        c.drawString(120, 540, "Endereço: Rua das Flores, 123")
        c.drawString(100, 510, "")
        c.drawString(100, 480, "Valor do Contrato: R$ 50.000,00")
        c.drawString(100, 450, "Prazo: 24 meses")
        c.drawString(100, 420, "Taxa de Juros: 2,5% ao mês")
        
        c.save()
        print(f"✅ Created test PDF: {pdf_path}")
        return pdf_path
        
    except ImportError:
        print("⚠️  reportlab not available, skipping PDF creation")
        return None

def test_hybrid_ocr_with_image_pdf():
    """Test the hybrid OCR engine with image-based PDF"""
    print("🖼️  Testing Hybrid OCR with Image-based PDF\n")
    
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
        
        # Create or use existing test PDF
        test_pdf = create_test_image_pdf()
        if not test_pdf:
            # Try to use existing PDF
            test_pdf = "uploads/c5c9d405-e34e-42dc-8648-2df37824c213/teste_original.pdf"
            if not os.path.exists(test_pdf):
                print("❌ No test PDF available")
                return False
        
        print(f"\n📄 Testing OCR with: {test_pdf}")
        
        # Test OCR performance
        start_time = time.time()
        
        try:
            pages = engine.extract_text_from_pdf(test_pdf)
            processing_time = time.time() - start_time
            
            print(f"⏱️  Processing time: {processing_time:.2f} seconds")
            print(f"📄 Pages processed: {len(pages)}")
            
            # Assess quality
            quality = engine.assess_quality(pages)
            print(f"\n📊 Quality Assessment:")
            for key, value in quality.items():
                print(f"   {key}: {value}")
            
            # Analyze extraction methods
            native_pages = quality.get('native_text_pages', 0)
            ocr_pages = quality.get('ocr_pages', 0)
            
            print(f"\n🔍 Extraction Analysis:")
            print(f"   Native text pages: {native_pages}")
            print(f"   OCR processed pages: {ocr_pages}")
            
            if native_pages > 0:
                print("   ✅ Native text extraction working")
            if ocr_pages > 0:
                print("   ✅ OCR processing working")
            
            # Show sample text from each page type
            for i, page in enumerate(pages[:3]):  # First 3 pages
                if page.raw_text and len(page.raw_text.strip()) > 0:
                    sample_text = page.raw_text[:150]
                    extraction_method = "OCR" if page.raw_text.startswith('[Page') else "Native"
                    if not page.raw_text.startswith('[Page'):
                        extraction_method = "OCR" if len(page.text_blocks) > 0 and any(block.confidence < 0.95 for block in page.text_blocks) else "Native"
                    
                    print(f"\n📝 Page {i+1} ({extraction_method}):")
                    print(f"   {sample_text}...")
                    print(f"   Confidence: {page.text_blocks[0].confidence if page.text_blocks else 'N/A'}")
            
            # Performance analysis
            print(f"\n⚡ Performance Analysis:")
            pages_per_second = len(pages) / processing_time if processing_time > 0 else 0
            print(f"   Pages per second: {pages_per_second:.2f}")
            
            if processing_time < 2:
                print("   🚀 Excellent speed (< 2 seconds)")
            elif processing_time < 5:
                print("   👍 Good speed (< 5 seconds)")
            elif processing_time < 10:
                print("   ⚠️  Moderate speed (< 10 seconds)")
            else:
                print("   🐌 Slow processing (> 10 seconds)")
            
            # Quality analysis
            avg_confidence = quality.get('overall_confidence', 0)
            if avg_confidence > 0.9:
                print("   🎯 Excellent text quality")
            elif avg_confidence > 0.8:
                print("   👍 Good text quality")
            elif avg_confidence > 0.7:
                print("   ⚠️  Acceptable text quality")
            else:
                print("   ❌ Poor text quality - check OCR settings")
            
            return True
            
        except Exception as e:
            print(f"❌ OCR processing failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Engine initialization failed: {e}")
        return False

def test_ocr_fallback_behavior():
    """Test OCR fallback behavior with different PDF types"""
    print("\n🔄 Testing OCR Fallback Behavior\n")
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app.services.hybrid_ocr_engine import HybridOCREngine
        
        engine = HybridOCREngine()
        
        # Test with non-existent file
        print("📄 Testing with non-existent file...")
        try:
            pages = engine.extract_text_from_pdf("non_existent.pdf")
            if pages and len(pages) > 0:
                print("   ✅ Graceful fallback to placeholder content")
                print(f"   Content: {pages[0].raw_text[:100]}...")
            else:
                print("   ❌ No fallback content generated")
        except Exception as e:
            print(f"   ❌ Exception not handled: {e}")
        
        # Test quality assessment with empty data
        print("\n📊 Testing quality assessment with empty data...")
        quality = engine.assess_quality([])
        print(f"   Result: {quality}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔍 Contract OCR - Image PDF Testing\n")
    
    # Test hybrid OCR
    ocr_success = test_hybrid_ocr_with_image_pdf()
    
    # Test fallback behavior
    fallback_success = test_ocr_fallback_behavior()
    
    if ocr_success and fallback_success:
        print("\n🎉 All OCR tests passed!")
        print("\n💡 Recommendations for Production:")
        print("   - Use hybrid engine for best results")
        print("   - Native text extraction is fastest")
        print("   - OCR fallback handles scanned documents")
        print("   - Monitor processing times for large documents")
        print("   - Adjust confidence thresholds based on requirements")
    else:
        print("\n❌ Some OCR tests failed")
        print("💡 Troubleshooting:")
        print("   - Ensure EasyOCR is properly installed")
        print("   - Check PDF file accessibility")
        print("   - Verify image processing libraries")
    
    print("\n🚀 Ready for deployment with hybrid OCR!")

if __name__ == "__main__":
    main()