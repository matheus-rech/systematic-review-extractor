# Server

This directory contains the Python backend for the systematic review extraction application.

## Components

### `verified_extraction_system.py`

Implements the `VerifiedExtractionSystem` class, which can scan a PDF for values matching regular expressions, compute a simple confidence score, record bounding box coordinates, capture screenshots, annotate PDFs, export extraction results to CSV/JSONL and generate audit reports.

### `mcp_verified_extraction_server.py`

Exposes the extraction engine through the [MCP protocol](https://github.com/microsoft/MCP).  The following tools are available:

* `health()` – check the server is responsive.
* `batch_extract_with_validation(pdf_path: str, extraction_template: str)` – run a batch extraction on a PDF using a JSON template.  Returns the extracted values and artifact filenames.
* `extract_table_data(pdf_path: str, table_identifier: str, target_cell: Optional[str])` – extract tables and optionally return a single cell value.
* `verify_llm_extraction(pdf_path: str, field_name: str, llm_claimed_value: str, llm_claimed_page: Optional[int])` – verify that a value claimed by a language model is present in the PDF.

Run the MCP server with:

```bash
python mcp_verified_extraction_server.py
```

### `bridge_http.py`

A [FastAPI](https://fastapi.tiangolo.com/) application that wraps the extraction engine with a REST API and static file serving.  The main endpoint is:

* `POST /api/batch_extract` – accepts a PDF and a JSON template and returns the extracted values as well as the names of generated artifacts.

The application also serves static files from the `verified_extractions` output directory.  See the repository root README for usage instructions.

## Installing dependencies

To install the dependencies for the server, run:

```bash
python -m pip install -r requirements.txt
```

## Development tips

* The `verified_extraction_system` module is self‑contained and can be imported in other scripts.  See the example in `bridge_http.py` for how to use it.
* Output directories are created automatically under `verified_extractions`.  Static files such as screenshots and annotated PDFs can be served directly by FastAPI or any other web server.
