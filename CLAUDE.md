# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a systematic review data extraction and verification application with hallucination-proof PDF extraction capabilities. It consists of a Python backend using FastAPI and PyMuPDF for PDF processing, and a React/Tailwind frontend for user interaction.

## Core Architecture

### Backend (`server/`)
- **`verified_extraction_system.py`**: Core extraction engine using regex-based pattern matching with coordinate tracking, screenshot capture, PDF annotation, and audit logging. Implements the `VerifiedExtractionSystem` class with methods for batch extraction, table extraction, and LLM claim verification.
- **`bridge_http.py`**: FastAPI REST API exposing `/api/batch_extract` endpoint for PDF processing. Serves static artifacts from `verified_extractions/` directory.
- **`mcp_verified_extraction_server.py`**: MCP protocol server providing programmatic access to extraction tools for automation.

### Frontend (`web/`)
- **`src/App.jsx`**: Single-page React application with extraction review interface, supporting verification/flagging/rejection of extracted data points with evidence visualization.
- Uses Vite for development server and build tooling.
- Tailwind CSS for styling.

### Data Flow
1. PDF + JSON template uploaded via web UI or API
2. Backend extracts values using regex patterns from template
3. System generates screenshots, annotated PDFs, audit logs
4. Frontend displays extractions with evidence for manual verification
5. User decisions exported as JSON with verification metadata

## Development Commands

### Backend Setup and Operations
```bash
# Setup Python environment
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run HTTP API server
uvicorn bridge_http:app --reload --port 8000

# Run MCP server (alternative interface)
python mcp_verified_extraction_server.py
```

### Frontend Setup and Operations
```bash
# Install dependencies
cd web
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Key Data Structures

### Extraction Template JSON Format
```json
{
  "field_name": {
    "patterns": ["regex1", "regex2"],  // List of regex patterns to match
    "hint": "description",              // Human-readable field description
    "required": true/false,             // Whether field is mandatory
    "type": "integer/float/string"      // Expected data type
  }
}
```

### ExtractedDataPoint
Contains: `field_name`, `value`, `page_number`, `coordinates`, `context`, `exact_text`, `confidence`, `extraction_method`, `timestamp`, `verification_hash`, `screenshot_path`, `source_type`

## Generated Artifacts Location
All extraction outputs are stored in `verified_extractions/`:
- `screenshots/`: PNG captures of extracted values
- `highlighted_pdfs/`: Annotated PDFs with highlights
- `audit_logs/`: Text audit reports
- `exports/`: CSV and JSONL export files
- `uploads/`: Uploaded PDF files

## API Endpoints

- `POST /api/batch_extract`: Main extraction endpoint accepting PDF and template files
- `GET /api/template`: Returns sample template JSON
- `GET /static/*`: Serves generated artifacts from output directory

## Testing Approach

The application currently does not have a formal test suite. When implementing tests:
- For backend: Use pytest with fixtures for PDF samples and templates
- For frontend: Use Vitest (already configured with Vite)
- Test extraction accuracy with known PDF samples
- Verify coordinate tracking and screenshot generation

## Important Implementation Details

- Pattern matching uses PyMuPDF's text extraction with bounding box preservation
- Confidence scoring is heuristic-based (see `_compute_confidence` method)
- Verification hashes bind extractions to specific PDF locations
- Frontend filters support search, status (pending/verified/flagged/rejected), and confidence thresholds
- All coordinates are stored as tuples (x0, y0, x1, y1) in PDF coordinate space

## Common Development Tasks

### Adding New Extraction Patterns
1. Update template JSON with new field definition
2. Add patterns array with regex expressions
3. Set appropriate type and required flags
4. Test with sample PDFs containing target data

### Modifying Confidence Scoring
Edit `_compute_confidence` method in `verified_extraction_system.py` to adjust heuristics based on field names and context keywords.

### Customizing UI Review Workflow
Modify `App.jsx` to add new verification statuses or interface elements. Current statuses: pending, verified, flagged, rejected.

### Debugging Extraction Issues
1. Check generated audit logs in `verified_extractions/audit_logs/`
2. Review annotated PDFs to see what was matched
3. Examine screenshots to verify coordinate accuracy
4. Use MCP server tools for programmatic testing