# Systematic Review Extraction and Verification App

[![Zero Hallucination Guarantee](https://img.shields.io/badge/Zero%20Hallucination-Guaranteed-green?style=for-the-badge&logo=shield&logoColor=white)](https://github.com/matheus-rech/systematic-review-extractor)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![React](https://img.shields.io/badge/react-18+-blue.svg)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-green.svg)](https://fastapi.tiangolo.com)

This repository contains a Python backend and a React/Tailwind frontend that work together to perform hallucination‑proof data extraction from PDFs for systematic reviews.

## Components

### Server (`server/`)

* `verified_extraction_system.py` – Core engine to extract values from PDFs with coordinate tracking, screenshots, annotated PDFs, CSV/JSONL exports and audit logs.  It exposes a `VerifiedExtractionSystem` class.
* `mcp_verified_extraction_server.py` – Implements an MCP server exposing several tools such as field extraction, batch extraction, LLM claim verification, table extraction and generation of annotations/audits from JSONL.
* `bridge_http.py` – FastAPI bridge that exposes REST endpoints around the `VerifiedExtractionSystem` for the web UI.  Endpoints include `/api/batch_extract` for uploading a PDF and template and triggering extraction.  The bridge also serves static files under `/static/*` from the `verified_extractions` directory.
* `requirements.txt` – Python dependencies.
* `README.md` – Additional details about running the server.

### Web (`web/`)

A Vite‑based React application written with Tailwind CSS that communicates with the Python backend.  The app lets you upload a PDF and an extraction template, view extracted data points, inspect evidence with context and screenshots, verify/flag/reject each extraction, add reviewer notes and export decisions.

Major files include:

* `package.json` – Node dependencies and scripts.
* `vite.config.js` – Vite configuration.
* `tailwind.config.js` and `postcss.config.js` – Tailwind CSS configuration.
* `index.html` – Base HTML entry.
* `src/main.jsx` – Entry point for the React app.
* `src/App.jsx` – Root component implementing the user interface.

## Getting Started

### Prerequisites

* **Python 3.8+**
* **Node.js 18+**

### Installing backend dependencies

```bash
cd server
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Running the HTTP bridge

```bash
uvicorn bridge_http:app --reload --port 8000
```

This starts the FastAPI server on port 8000.  It will create an output directory `verified_extractions` for generated artifacts and serve them under `/static`.

### Running the MCP server (optional)

If you want to use the MCP protocol instead of HTTP, run:

```bash
python mcp_verified_extraction_server.py
```

### Installing web dependencies

```bash
cd ../web
npm install
```

### Running the web UI

```bash
npm run dev
```

Open the URL shown in the terminal (usually http://localhost:5173) in your browser.  By default, the app expects the backend at `http://localhost:8000`, but you can change this in the UI.

### Running an extraction

1. Start the HTTP bridge server.
2. Visit the web UI.
3. Upload a PDF and a JSON template (an example is provided at the repository root as `sample_template.json`).
4. After processing, extracted data points will appear on the left.  Click any item to see its evidence, verification hash and screenshot (if generated).
5. Use the verify/flag/reject buttons to record decisions.  The progress bar updates automatically.
6. Use the export button to download your decisions as JSON.

For more advanced usage, see the documentation in each subdirectory.

## License

MIT License
