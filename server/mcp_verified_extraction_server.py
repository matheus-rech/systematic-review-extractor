"""
MCP server wrapper for the VerifiedExtractionSystem.

This module exposes a set of tools via the MCP protocol so that other
automated systems can call the extractor programmatically.  The tools
include batch extraction, table extraction and LLM claim verification.
"""

from __future__ import annotations

import json
from typing import Dict, Any, Optional, List

import fitz  # PyMuPDF
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

from .verified_extraction_system import VerifiedExtractionSystem

# Instantiate a FastMCP server
mcp = FastMCP(name="verified_extraction_server")

# Single global extraction system instance
system = VerifiedExtractionSystem()


@mcp.tool()
async def health() -> Dict[str, Any]:
    """
    Simple health check to ensure the server is responsive.
    """
    return {"status": "ok"}


@mcp.tool()
async def batch_extract_with_validation(
    pdf_path: str,
    extraction_template: str,
    ) -> Dict[str, Any]:
    """
    Perform a batch extraction on a PDF given a JSON template string.

    The template should follow the same structure as `sample_template.json`.
    The response contains a list of extracted values, along with filenames for
    the annotated PDF, audit report and export files.
    """
    try:
        template = json.loads(extraction_template)
    except Exception as e:
        return {"status": "error", "message": f"Invalid template: {e}"}
    exts = system.extract_by_template(pdf_path, template)
    annotated = system.highlight_pdf_with_extractions(pdf_path, exts)
    audit = system.create_audit_report(pdf_path, exts)
    csv_file = system.export_extractions_to_csv(exts)
    jsonl_file = system.export_extractions_to_jsonl(exts)
    return {
        "status": "success",
        "extractions": [ext.to_dict() for ext in exts],
        "annotated_pdf": annotated,
        "audit_log": audit,
        "csv": csv_file,
        "jsonl": jsonl_file,
    }


@mcp.tool()
async def extract_table_data(
    pdf_path: str, table_identifier: str, target_cell: Optional[str] = None
    ) -> Dict[str, Any]:
    """
    Extract tables from a PDF and optionally return a specific cell value.

    `table_identifier` should be a phrase contained within the table text.
    `target_cell` may be of the form `"row:2,col:3"` to extract a single cell.
    """
    tables = system.extract_tables_with_location(pdf_path)
    found: List[Dict[str, Any]] = []
    for tbl in tables:
        # Flatten table data into a string for identification
        flat = " ".join([" ".join(row) for row in tbl["data"] if row])
        if table_identifier.lower() in flat.lower():
            info = tbl.copy()
            if target_cell:
                try:
                    parts = target_cell.split(",")
                    row_idx = int(parts[0].split(":")[1])
                    col_idx = int(parts[1].split(":")[1])
                    if 0 <= row_idx < len(tbl["data"]) and 0 <= col_idx < len(
                        tbl["data"][row_idx]
                    ):
                        info["extracted_value"] = tbl["data"][row_idx][col_idx]
                except Exception:
                    pass
            found.append(info)
    if found:
        return {"status": "success", "tables": found}
    else:
        return {"status": "not_found", "message": "Table not found"}


@mcp.tool()
async def verify_llm_extraction(
    pdf_path: str,
    field_name: str,
    llm_claimed_value: str,
    llm_claimed_page: Optional[int] = None,
    ) -> Dict[str, Any]:
    """
    Verify an LLM‑claimed extraction by searching the PDF for the claimed value.

    If `llm_claimed_page` is provided, only that page will be searched.
    Otherwise all pages are scanned.  The result includes contextual evidence
    if a match is found.
    """
    doc = fitz.open(pdf_path)
    pages = (
        [llm_claimed_page - 1]
        if llm_claimed_page
        else list(range(len(doc)))
    )
    evidence = []
    found = False
    for page_idx in pages:
        if page_idx < 0 or page_idx >= len(doc):
            continue
        page = doc[page_idx]
        text = page.get_text()
        if llm_claimed_value.lower() in text.lower():
            found = True
            insts = page.search_for(llm_claimed_value)
            for inst in insts:
                # Extract context around the first occurrence
                idx = text.lower().find(llm_claimed_value.lower())
                start = max(0, idx - 100)
                end = min(len(text), idx + len(llm_claimed_value) + 100)
                context = text[start:end]
                evidence.append(
                    {
                        "page": page_idx + 1,
                        "coordinates": (inst.x0, inst.y0, inst.x1, inst.y1),
                        "context": context,
                    }
                )
    doc.close()
    if found:
        return {
            "status": "VERIFIED",
            "field_name": field_name,
            "claimed_value": llm_claimed_value,
            "evidence": evidence,
        }
    else:
        return {
            "status": "NOT_VERIFIED",
            "field_name": field_name,
            "claimed_value": llm_claimed_value,
            "evidence": [],
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
