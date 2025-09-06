#!/bin/bash

echo "========================================"
echo "Installing PDF Processing Dependencies"
echo "========================================"

# Check Python version
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

echo "Installing Python packages..."

# Core packages
pip install --upgrade pip
pip install PyMuPDF==1.23.8
pip install pillow==10.1.0
pip install numpy==1.24.3
pip install pandas==2.0.3

# Table extraction
pip install camelot-py[cv]==0.11.0
pip install opencv-python==4.8.1.78

# OCR capabilities
pip install pytesseract==0.3.10
pip install pdf2image==1.16.3

# Web interface
pip install flask==3.0.0
pip install flask-cors==4.0.0

# Additional utilities
pip install python-magic==0.4.27

echo ""
echo "========================================"
echo "Installing System Dependencies"
echo "========================================"

# Check OS and install system dependencies
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected. Installing with Homebrew..."
    
    # Install Homebrew if not present
    if ! command -v brew &> /dev/null; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Install system dependencies
    brew install ghostscript
    brew install tesseract
    brew install poppler
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Linux detected. Installing with apt..."
    
    sudo apt-get update
    sudo apt-get install -y \
        ghostscript \
        python3-tk \
        tesseract-ocr \
        libtesseract-dev \
        poppler-utils \
        libgl1-mesa-glx
        
else
    echo "Windows detected. Please install manually:"
    echo "1. Ghostscript: https://www.ghostscript.com/download/gsdnld.html"
    echo "2. Tesseract: https://github.com/UB-Mannheim/tesseract/wiki"
    echo "3. Poppler: https://blog.alivate.com.au/poppler-windows/"
fi

echo ""
echo "========================================"
echo "Verifying Installation"
echo "========================================"

# Test imports
python3 -c "
import sys
print('Python:', sys.version)
try:
    import fitz
    print('✓ PyMuPDF installed')
except ImportError as e:
    print('✗ PyMuPDF failed:', e)

try:
    import camelot
    print('✓ Camelot installed')
except ImportError as e:
    print('✗ Camelot failed:', e)

try:
    import pytesseract
    print('✓ Pytesseract installed')
except ImportError as e:
    print('✗ Pytesseract failed:', e)

try:
    import cv2
    print('✓ OpenCV installed')
except ImportError as e:
    print('✗ OpenCV failed:', e)

try:
    from pdf2image import convert_from_path
    print('✓ pdf2image installed')
except ImportError as e:
    print('✗ pdf2image failed:', e)

try:
    import flask
    print('✓ Flask installed')
except ImportError as e:
    print('✗ Flask failed:', e)
"

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "To run the PDF processor:"
echo "1. Activate environment: source .venv/bin/activate"
echo "2. Run: python real_pdf_processor.py"
echo "3. Open: http://localhost:5000"
echo ""
echo "The system can now process:"
echo "✓ Regular PDF text"
echo "✓ Tables (bordered and borderless)"
echo "✓ Images and figures"
echo "✓ Scanned/OCR content"
echo ""