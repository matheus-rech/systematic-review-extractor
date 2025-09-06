"""
HTTP bridge for the VerifiedExtractionSystem.

This FastAPI application exposes a simple REST interface over the extraction
engine.  It accepts file uploads for PDFs and JSON templates, performs a
batch extraction and returns the results along with names of generated
artifacts.  It also serves static files (screenshots, annotated PDFs, logs)
from the extraction output directory.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .verified_extraction_system import VerifiedExtractionSystem

# Instantiate FastAPI and extraction system
app = FastAPI(title="Systematic Review Extraction API")
system = VerifiedExtractionSystem()

# Mount static file serving for generated artifacts
app.mount(
    "/static",
    StaticFiles(directory=system.output_dir, html=True),
    name="static",
)


@app.post("/api/batch_extract")
async def batch_extract(
    pdf_file: UploadFile = File(...),
    template_file: UploadFile = File(...),
):
    """
    Run a batch extraction on the uploaded PDF using the provided JSON template.

    Returns a JSON object containing the extracted values and filenames of
    generated artifacts.  The client can fetch the files via `/static/{filename}`.
    """
    # Persist uploaded PDF
    uploads_dir = system.output_dir / "uploads"
    pdf_path = uploads_dir / pdf_file.filename
    with open(pdf_path, "wb") as f:
        content = await pdf_file.read()
        f.write(content)
    # Parse template
    try:
        tpl_bytes = await template_file.read()
        template_json = json.loads(tpl_bytes.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid template JSON: {e}")
    # Run extraction
    extractions = system.extract_by_template(str(pdf_path), template_json)
    annotated_pdf = system.highlight_pdf_with_extractions(str(pdf_path), extractions)
    audit_log = system.create_audit_report(str(pdf_path), extractions)
    csv_file = system.export_extractions_to_csv(extractions)
    jsonl_file = system.export_extractions_to_jsonl(extractions)
    # Build response
    return JSONResponse(
        {
            "extractions": [ext.to_dict() for ext in extractions],
            "annotated_pdf": annotated_pdf,
            "audit_log": audit_log,
            "csv": csv_file,
            "jsonl": jsonl_file,
        }
    )


@app.get("/api/template")
async def get_default_template():
    """
    Return the example extraction template included with the repository.
    """
    template_path = (
        Path(__file__).resolve().parent.parent / "sample_template.json"
    )
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    with open(template_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(data)
