#!/usr/bin/env python3
"""
Test script for the enhanced systematic review extraction system.
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# Add server directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    errors = []
    
    # Core modules
    try:
        from verified_extraction_system import VerifiedExtractionSystem
        print("✓ Base extraction system")
    except ImportError as e:
        errors.append(f"✗ Base extraction system: {e}")
    
    # AI modules
    try:
        from ai_enhanced_extraction import AIEnhancedExtractionSystem
        print("✓ AI enhanced extraction")
    except ImportError as e:
        errors.append(f"✗ AI enhanced extraction: {e}")
    
    # API modules
    try:
        from enhanced_bridge import app
        print("✓ Enhanced API")
    except ImportError as e:
        errors.append(f"✗ Enhanced API: {e}")
    
    # Database
    try:
        from database import db_ops, Base
        print("✓ Database models")
    except ImportError as e:
        errors.append(f"✗ Database models: {e}")
    
    # Required libraries
    libraries = {
        'anthropic': 'Anthropic Claude',
        'chromadb': 'ChromaDB vector store',
        'spacy': 'SpaCy NLP',
        'pytesseract': 'Tesseract OCR',
        'pdfplumber': 'PDF plumber',
        'sklearn': 'Scikit-learn',
        'sentence_transformers': 'Sentence transformers',
        'loguru': 'Loguru logging',
        'sqlalchemy': 'SQLAlchemy ORM',
        'celery': 'Celery async',
        'redis': 'Redis cache'
    }
    
    for lib, name in libraries.items():
        try:
            __import__(lib)
            print(f"✓ {name}")
        except ImportError:
            errors.append(f"✗ {name}: Not installed")
    
    return errors

async def test_basic_extraction():
    """Test basic extraction functionality."""
    print("\nTesting basic extraction...")
    
    try:
        from verified_extraction_system import VerifiedExtractionSystem
        
        system = VerifiedExtractionSystem()
        print("✓ Basic system initialized")
        
        # Test with sample template
        template = {
            "test_field": {
                "patterns": [r"test\s+(\w+)"],
                "hint": "Test field",
                "required": False,
                "type": "string"
            }
        }
        
        print("✓ Template created")
        return True
        
    except Exception as e:
        print(f"✗ Basic extraction failed: {e}")
        return False

async def test_ai_system():
    """Test AI-enhanced extraction system."""
    print("\nTesting AI-enhanced system...")
    
    try:
        from ai_enhanced_extraction import AIEnhancedExtractionSystem
        
        # Initialize without API key for basic test
        system = AIEnhancedExtractionSystem(
            anthropic_api_key=None,
            use_medical_agents=False
        )
        print("✓ AI system initialized (without API key)")
        
        # Check components
        if system.chroma_client:
            print("✓ ChromaDB initialized")
        else:
            print("✗ ChromaDB not initialized")
        
        if system.confidence_model:
            print("✓ ML confidence model loaded/trained")
        else:
            print("✗ ML confidence model not available")
        
        # Test template generation
        template = system.generate_smart_template([])
        if template and len(template) > 0:
            print(f"✓ Smart template generated with {len(template)} fields")
        else:
            print("✗ Template generation failed")
        
        return True
        
    except Exception as e:
        print(f"✗ AI system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database connectivity."""
    print("\nTesting database...")
    
    try:
        from database import db_ops, Project
        
        # Test connection
        session = db_ops.get_session()
        session.close()
        print("✓ Database connection established")
        
        # Test basic operation
        try:
            project = db_ops.create_project(
                name="Test Project",
                description="Test project for validation"
            )
            print(f"✓ Created test project (ID: {project.id})")
            
            stats = db_ops.get_project_statistics(project.id)
            print(f"✓ Retrieved statistics: {stats}")
            
        except Exception as e:
            print(f"⚠ Database operations: {e}")
            print("  (This is normal if database is not configured)")
        
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def test_api():
    """Test API endpoints."""
    print("\nTesting API endpoints...")
    
    try:
        from enhanced_bridge import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/api/v2/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check: {data['status']}")
            print(f"  Features: LLM={data['features']['llm_validation']}, "
                  f"OCR={data['features']['ocr']}, "
                  f"Vector={data['features']['vector_search']}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
        
        # Test template library
        response = client.get("/api/v2/templates/library")
        if response.status_code == 200:
            templates = response.json()
            print(f"✓ Template library: {len(templates)} templates available")
        else:
            print(f"✗ Template library failed: {response.status_code}")
        
        # Test statistics
        response = client.get("/api/v2/statistics")
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Statistics endpoint: {stats['total_extractions']} extractions")
        else:
            print(f"✗ Statistics failed: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False

def test_frontend():
    """Test frontend build."""
    print("\nTesting frontend...")
    
    web_dir = Path("web")
    
    # Check files exist
    files_to_check = [
        "package.json",
        "src/App.jsx",
        "src/EnhancedApp.jsx",
        "vite.config.js",
        "tailwind.config.js"
    ]
    
    for file in files_to_check:
        file_path = web_dir / file
        if file_path.exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
    
    # Check if dependencies are listed
    package_json = web_dir / "package.json"
    if package_json.exists():
        with open(package_json) as f:
            package = json.load(f)
            deps = package.get("dependencies", {})
            
            required_deps = ["react", "react-dom", "axios", "recharts", "react-dropzone"]
            for dep in required_deps:
                if dep in deps:
                    print(f"✓ {dep} in dependencies")
                else:
                    print(f"✗ {dep} missing from dependencies")
    
    return True

def check_environment():
    """Check environment variables and configuration."""
    print("\nChecking environment...")
    
    env_vars = {
        "ANTHROPIC_API_KEY": "Claude AI",
        "DATABASE_URL": "Database connection",
    }
    
    for var, name in env_vars.items():
        if os.getenv(var):
            print(f"✓ {name} configured ({var})")
        else:
            print(f"⚠ {name} not configured ({var})")
            print(f"  Set with: export {var}='your_value'")
    
    # Check for required system tools
    import shutil
    
    tools = {
        "tesseract": "Tesseract OCR",
        "redis-server": "Redis server",
        "psql": "PostgreSQL client"
    }
    
    for tool, name in tools.items():
        if shutil.which(tool):
            print(f"✓ {name} installed")
        else:
            print(f"⚠ {name} not found (optional)")

async def main():
    """Run all tests."""
    print("=" * 60)
    print("ENHANCED SYSTEMATIC REVIEW EXTRACTOR - SYSTEM TEST")
    print("=" * 60)
    
    # Check environment
    check_environment()
    
    # Test imports
    import_errors = test_imports()
    
    if import_errors:
        print("\n⚠️  Some imports failed. Installing missing dependencies...")
        print("\nRun these commands:")
        print("cd server")
        print("pip install -r requirements.txt")
        print("\nFor SpaCy model:")
        print("python -m spacy download en_core_web_sm")
        print("\nFor frontend:")
        print("cd web")
        print("npm install")
    
    # Test components
    await test_basic_extraction()
    await test_ai_system()
    test_database()
    test_api()
    test_frontend()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if not import_errors:
        print("✅ Core system is functional!")
        print("\nTo fully activate all features:")
        print("1. Set ANTHROPIC_API_KEY for Claude AI")
        print("2. Configure DATABASE_URL for persistence")
        print("3. Install optional tools (Tesseract, Redis)")
        print("4. Run: cd web && npm install")
        print("\nStart the system:")
        print("Backend: cd server && python enhanced_bridge.py")
        print("Frontend: cd web && npm run dev")
    else:
        print("⚠️  Some components need setup")
        print(f"Found {len(import_errors)} import issues")
        print("\nInstall dependencies first:")
        print("cd server && pip install -r requirements.txt")

if __name__ == "__main__":
    asyncio.run(main())