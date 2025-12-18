#!/usr/bin/env python3
"""
Development setup verification script
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_imports():
    """Check if core dependencies can be imported"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        import sqlalchemy
        import alembic
        print("✓ Core dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def check_app():
    """Check if the main app can be imported"""
    try:
        from app.main import app
        print("✓ FastAPI application imported successfully")
        return True
    except ImportError as e:
        print(f"✗ App import error: {e}")
        return False

def check_directories():
    """Check if required directories exist"""
    required_dirs = ['app', 'tests', 'uploads', 'alembic']
    all_exist = True
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✓ Directory '{dir_name}' exists")
        else:
            print(f"✗ Directory '{dir_name}' missing")
            all_exist = False
    
    return all_exist

def main():
    """Run all checks"""
    print("Contract OCR API - Development Setup Check")
    print("=" * 45)
    
    checks = [
        ("Core Dependencies", check_imports),
        ("Application Import", check_app),
        ("Directory Structure", check_directories)
    ]
    
    all_passed = True
    for name, check_func in checks:
        print(f"\n{name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 45)
    if all_passed:
        print("✓ All checks passed! Development environment is ready.")
        print("\nNext steps:")
        print("1. Run tests: python -m pytest")
        print("2. Start development server: python run.py")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())