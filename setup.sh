#!/bin/bash

echo "=========================================="
echo "Systematic Review Extractor - Setup Script"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 is required but not found."
    echo "Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip --quiet

# Install requirements
echo ""
echo "Installing required packages..."
pip install -r requirements.txt

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "
import sys
print(f'Python: {sys.version}')
try:
    import fitz
    print('✓ PyMuPDF installed successfully')
except ImportError:
    print('❌ PyMuPDF installation failed')
    sys.exit(1)

try:
    import PIL
    print('✓ Pillow installed successfully')
except ImportError:
    print('❌ Pillow installation failed')
    sys.exit(1)

try:
    import numpy
    print('✓ NumPy installed successfully')
except ImportError:
    print('❌ NumPy installation failed')
    sys.exit(1)

try:
    import pandas
    print('✓ Pandas installed successfully')
except ImportError:
    print('❌ Pandas installation failed')
    sys.exit(1)

print('')
print('✅ All core dependencies installed successfully!')
"

# Create example directory
echo ""
echo "Setting up example files..."
mkdir -p examples
mkdir -p templates

# Test the system
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "To use the system:"
echo "1. Activate the environment: source .venv/bin/activate"
echo "2. Run extraction: python systematic_review_pipeline.py your_paper.pdf"
echo ""
echo "For help: python systematic_review_pipeline.py --help"
echo ""
echo "Templates available in: templates/"
echo "User guide available in: USER_GUIDE.md"
echo ""