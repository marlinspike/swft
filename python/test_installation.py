#!/usr/bin/env python3
"""
Test script to verify vulnerable packages are installed and working
"""

import sys
import importlib

def test_package_import(package_name, version_attr='__version__'):
    """Test if a package can be imported and get its version"""
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, version_attr, 'unknown')
        print(f"✓ {package_name}: {version}")
        return True
    except ImportError as e:
        print(f"✗ {package_name}: Import failed - {e}")
        return False
    except Exception as e:
        print(f"? {package_name}: Available but version check failed - {e}")
        return True

def test_fastapi_compatibility():
    """Test if FastAPI and Pydantic work together"""
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
        
        app = FastAPI()
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        @app.get("/test")
        def test_endpoint():
            return {"message": "test"}
        
        print("✓ FastAPI + Pydantic compatibility: OK")
        return True
    except Exception as e:
        print(f"✗ FastAPI + Pydantic compatibility: FAILED - {e}")
        return False

def main():
    print("Testing vulnerable package installation...")
    print(f"Python version: {sys.version}")
    print()
    
    # Test core vulnerable packages
    packages = [
        ('fastapi', '__version__'),
        ('uvicorn', '__version__'),
        ('jinja2', '__version__'),
        ('markupsafe', '__version__'),
        ('pydantic', 'VERSION'),
        ('requests', '__version__'),
        ('urllib3', '__version__'),
        ('flask', '__version__'),
        ('werkzeug', '__version__'),
        ('click', '__version__'),
    ]
    
    success_count = 0
    total_count = len(packages)
    
    for package, version_attr in packages:
        if test_package_import(package, version_attr):
            success_count += 1
    
    print()
    print("Testing FastAPI compatibility...")
    fastapi_ok = test_fastapi_compatibility()
    
    print()
    print(f"Results: {success_count}/{total_count} packages imported successfully")
    if fastapi_ok:
        print("✓ FastAPI compatibility test passed")
    else:
        print("✗ FastAPI compatibility test failed")
    
    if success_count == total_count and fastapi_ok:
        print("\n🎉 All tests passed! Ready for Trivy scanning.")
        return 0
    else:
        print(f"\n⚠️  Some issues found. {total_count - success_count} packages failed to import.")
        return 1

if __name__ == "__main__":
    sys.exit(main())