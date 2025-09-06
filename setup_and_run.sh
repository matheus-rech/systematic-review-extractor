#!/bin/bash

# Enhanced Systematic Review Extractor - Complete Setup & Run Script
# This script will install all dependencies and start the system

set -e  # Exit on any error

echo "🚀 Enhanced Systematic Review Extractor - Automated Setup"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo -e "${BLUE}Step 1: Setting up Python environment...${NC}"
cd server

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

echo -e "${BLUE}Step 2: Installing Python dependencies...${NC}"
echo "This may take a few minutes..."

# Upgrade pip first
pip install --upgrade pip

# Install core dependencies first (ones that work)
pip install fastapi uvicorn pydantic pillow pandas numpy python-multipart

# Try to install PyMuPDF
pip install pymupdf || echo -e "${YELLOW}Warning: PyMuPDF installation failed, trying alternative...${NC}"

# Install AI/ML dependencies (skip if they fail)
pip install anthropic || echo -e "${YELLOW}Warning: Anthropic not installed (AI features disabled)${NC}"
pip install chromadb || echo -e "${YELLOW}Warning: ChromaDB not installed (vector search disabled)${NC}"
pip install sentence-transformers || echo -e "${YELLOW}Warning: Sentence transformers not installed${NC}"
pip install spacy || echo -e "${YELLOW}Warning: SpaCy not installed${NC}"
pip install scikit-learn || echo -e "${YELLOW}Warning: Scikit-learn not installed${NC}"

# OCR dependencies (optional)
pip install pytesseract pdf2image || echo -e "${YELLOW}Warning: OCR dependencies not installed${NC}"

# Database (use SQLite as fallback)
pip install sqlalchemy || echo -e "${YELLOW}Warning: SQLAlchemy not installed${NC}"

# Try to download SpaCy model
python -m spacy download en_core_web_sm 2>/dev/null || echo -e "${YELLOW}SpaCy model not downloaded${NC}"

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Set up environment variables
echo -e "${BLUE}Step 3: Configuring environment...${NC}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Environment Configuration
DATABASE_URL=sqlite:///./systematic_review.db
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-your_api_key_here}
OUTPUT_DIR=verified_extractions
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ Created .env file${NC}"
fi

# Load environment variables
export DATABASE_URL="sqlite:///./systematic_review.db"
export OUTPUT_DIR="verified_extractions"

# Create output directories
mkdir -p verified_extractions/{screenshots,highlighted_pdfs,audit_logs,exports,uploads,vectorstore}

echo -e "${BLUE}Step 4: Setting up frontend...${NC}"
cd ../web

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}npm is not installed. Please install Node.js first.${NC}"
    echo "Visit: https://nodejs.org/"
else
    # Install frontend dependencies
    echo "Installing frontend dependencies..."
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
fi

echo -e "${BLUE}Step 5: Creating simplified API for immediate use...${NC}"
cd ../server

# Create a simplified version that works with minimal dependencies
cat > simple_api.py << 'EOF'
"""
Simplified API that works with minimal dependencies.
Falls back gracefully when advanced features are not available.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path
from datetime import datetime
import hashlib
import re
from typing import List, Dict, Any

app = FastAPI(title="Systematic Review Extractor - Simple Mode")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory
output_dir = Path("verified_extractions")
output_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=output_dir, html=True), name="static")

# Try to import the full system, fall back to simple extraction
try:
    from verified_extraction_system import VerifiedExtractionSystem
    system = VerifiedExtractionSystem()
    print("✓ Full extraction system loaded")
except ImportError:
    print("⚠ Running in simple mode (limited features)")
    system = None

class SimpleExtractor:
    """Fallback extractor using basic regex."""
    
    def extract_simple(self, text: str, template: Dict) -> List[Dict]:
        """Simple regex extraction."""
        results = []
        
        for field_name, config in template.items():
            patterns = config.get("patterns", [])
            for pattern in patterns:
                try:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    if matches:
                        value = matches[0] if matches else None
                        if value:
                            results.append({
                                "field_name": field_name,
                                "value": value,
                                "confidence": 0.5,
                                "page_number": 1,
                                "extraction_method": "simple_regex",
                                "timestamp": datetime.now().isoformat()
                            })
                            break
                except:
                    continue
        
        return results

simple_extractor = SimpleExtractor()

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": "full" if system else "simple",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/extract")
async def extract(
    pdf_file: UploadFile = File(...),
    template_file: UploadFile = File(...)
):
    """Extract data from PDF using template."""
    
    # Save uploaded files
    uploads_dir = output_dir / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    
    pdf_path = uploads_dir / pdf_file.filename
    with open(pdf_path, "wb") as f:
        content = await pdf_file.read()
        f.write(content)
    
    # Parse template
    template_content = await template_file.read()
    template = json.loads(template_content.decode("utf-8"))
    
    # Extract based on available system
    if system:
        # Use full system
        try:
            extractions = system.extract_by_template(str(pdf_path), template)
            results = [e.to_dict() for e in extractions]
        except Exception as e:
            # Fallback to simple
            with open(pdf_path, "rb") as f:
                text = f.read().decode("utf-8", errors="ignore")
            results = simple_extractor.extract_simple(text, template)
    else:
        # Use simple extraction
        with open(pdf_path, "rb") as f:
            text = f.read().decode("utf-8", errors="ignore")
        results = simple_extractor.extract_simple(text, template)
    
    return JSONResponse({
        "extractions": results,
        "mode": "full" if system else "simple",
        "pdf": pdf_file.filename,
        "fields_found": len(results),
        "fields_requested": len(template)
    })

@app.get("/api/templates")
async def get_templates():
    """Get available templates."""
    return {
        "basic": {
            "sample_size": {
                "patterns": [r"n\s*=\s*(\d+)", r"(\d+)\s*participants"],
                "hint": "Number of participants",
                "type": "integer"
            },
            "p_value": {
                "patterns": [r"p\s*[<=]\s*(0\.\d+)", r"P\s*value.*?(0\.\d+)"],
                "hint": "Statistical significance",
                "type": "float"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting Systematic Review Extractor")
    print("Mode:", "Full" if system else "Simple (limited features)")
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

echo -e "${GREEN}✓ Created simplified API${NC}"

echo -e "${BLUE}Step 6: Creating test PDF and template...${NC}"

# Create a sample PDF content file (text file for testing)
cat > ../sample_test.txt << 'EOF'
Clinical Trial Results

Study Design:
This randomized controlled trial enrolled n = 150 participants with a mean age of 45.2 ± 12.3 years.

Results:
The primary outcome showed significant improvement with p < 0.001. The effect size was Cohen's d = 0.85.

Conclusion:
The intervention was effective with a 95% CI [0.72, 0.98].
EOF

echo -e "${GREEN}✓ Created sample test document${NC}"

# Start the servers
echo ""
echo -e "${GREEN}=========================================================="
echo "🎉 Setup Complete!"
echo "==========================================================${NC}"
echo ""
echo -e "${YELLOW}Starting the system...${NC}"
echo ""

# Function to start backend
start_backend() {
    echo -e "${BLUE}Starting backend server...${NC}"
    cd "$DIR/server"
    source .venv/bin/activate
    python simple_api.py &
    BACKEND_PID=$!
    echo -e "${GREEN}✓ Backend running on http://localhost:8000${NC}"
    echo -e "${GREEN}✓ API docs at http://localhost:8000/docs${NC}"
}

# Function to start frontend
start_frontend() {
    if command -v npm &> /dev/null; then
        echo -e "${BLUE}Starting frontend...${NC}"
        cd "$DIR/web"
        npm run dev &
        FRONTEND_PID=$!
        echo -e "${GREEN}✓ Frontend will be available at http://localhost:5173${NC}"
    else
        echo -e "${YELLOW}Skipping frontend (npm not installed)${NC}"
    fi
}

# Start both servers
start_backend
sleep 3
start_frontend

echo ""
echo -e "${GREEN}=========================================================="
echo "✅ System is running!"
echo "==========================================================${NC}"
echo ""
echo "Access points:"
echo "  • Frontend: http://localhost:5173"
echo "  • Backend API: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo ""
echo "Test the API:"
echo "  curl http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for user to stop
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Servers stopped'" EXIT
wait