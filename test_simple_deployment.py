#!/usr/bin/env python3
"""
Test script to verify the simplified deployment works
"""
import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test core dependencies
        import fastapi
        print("✅ FastAPI imported successfully")
        
        import uvicorn
        print("✅ Uvicorn imported successfully")
        
        import sqlalchemy
        print("✅ SQLAlchemy imported successfully")
        
        try:
            import psycopg2
            print("✅ psycopg2 imported successfully")
        except ImportError:
            print("⚠️  psycopg2 not available (OK for local testing)")
        
        # Test PDF libraries
        pdf_lib = None
        try:
            import pdfplumber
            pdf_lib = "pdfplumber"
            print("✅ pdfplumber imported successfully")
        except ImportError:
            try:
                import pypdf
                pdf_lib = "pypdf"
                print("✅ pypdf imported successfully")
            except ImportError:
                print("⚠️  No PDF library available")
        
        # Test our modules
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from app.services.ocr_engine_simple import SimpleOCREngine
        print("✅ SimpleOCREngine imported successfully")
        
        from app.core.config import settings
        print("✅ Settings imported successfully")
        
        from app.main import app
        print("✅ FastAPI app imported successfully")
        
        # Test OCR engine initialization
        ocr = SimpleOCREngine()
        engines = ocr.get_available_engines()
        print(f"✅ OCR engine initialized with: {engines}")
        
        return True, pdf_lib
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False, None

def test_basic_functionality():
    """Test basic functionality"""
    print("\nTesting basic functionality...")
    
    try:
        from app.services.ocr_engine_simple import SimpleOCREngine
        
        ocr = SimpleOCREngine()
        
        # Test quality assessment with empty data
        quality = ocr.assess_quality([])
        print(f"✅ Quality assessment works: {quality}")
        
        # Test available engines
        engines = ocr.get_available_engines()
        print(f"✅ Available engines: {engines}")
        
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Testing Contract OCR API Deployment Compatibility\n")
    
    # Test imports
    imports_ok, pdf_lib = test_imports()
    
    if not imports_ok:
        print("\n❌ Import tests failed!")
        sys.exit(1)
    
    # Test basic functionality
    functionality_ok = test_basic_functionality()
    
    if not functionality_ok:
        print("\n❌ Functionality tests failed!")
        sys.exit(1)
    
    print("\n🎉 All tests passed!")
    print(f"📚 PDF Library: {pdf_lib or 'None (placeholder mode)'}")
    print("✅ Ready for deployment!")

if __name__ == "__main__":
    main()