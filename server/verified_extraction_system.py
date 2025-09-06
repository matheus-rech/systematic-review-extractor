"""
Core engine for hallucination‑proof data extraction from PDFs.

This module defines a dataclass for representing extracted data points and a
`VerifiedExtractionSystem` class that can:
  • Scan a PDF for values matching regular expressions.
  • Compute a simple confidence score based on the surrounding context.
  • Record the page and bounding box coordinates for each match.
  • Capture a zoomed screenshot of each match with a highlight overlay.
  • Annotate the original PDF with colored highlights and inline notes.
  • Export extraction results to CSV and JSONL formats.
  • Generate a lightweight audit report summarising all extractions.
"""

from __future__ import annotations

import json
import hashlib
import datetime
import re
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Any, Dict
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ExtractedDataPoint:
    """Represents a single extracted value with provenance information."""
    field_name: str
    value: Any
    page_number: int
    coordinates: Tuple[float, float, float, float]
    context: str
    exact_text: str
    confidence: float
    extraction_method: str
    timestamp: str
    verification_hash: str
    screenshot_path: Optional[str] = None
    source_type: str = "text"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VerifiedExtractionSystem:
    """A comprehensive PDF extraction engine with provenance and audit support."""

    def __init__(self, output_dir: str = "verified_extractions") -> None:
        self.output_dir = Path(output_dir)
        # Create subdirectories to store artifacts
        for sub in ["screenshots", "highlighted_pdfs", "audit_logs", "exports", "uploads"]:
            (self.output_dir / sub).mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _compute_confidence(self, field_name: str, value: str, context: str) -> float:
        """
        Rough heuristic to score the plausibility of a match based on its context.
        Starts at 0.5 and increments for desirable keywords and section clues.
        """
        score = 0.5
        lc_field = field_name.lower()
        lc_ctx = context.lower()
        if "mean" in lc_field or "average" in lc_ctx:
            score += 0.1
        if "participants" in lc_ctx or "subjects" in lc_ctx:
            score += 0.1
        if "p" in lc_field:
            score += 0.1
        if "table" in lc_ctx or "|" in context:
            score += 0.1
        if "results" in lc_ctx or "methods" in lc_ctx:
            score += 0.1
        return min(score, 1.0)

    def create_verification_hash(
        self, pdf_path: str, page_number: int, rect: Tuple[float, float, float, float], text: str
    ) -> str:
        """
        Build a short hash binding the extraction to its source document and location.
        """
        joined = f"{Path(pdf_path).resolve()}|{page_number}|{rect}|{text}"
        return hashlib.sha256(joined.encode()).hexdigest()[:16]

    def capture_screenshot(
        self,
        pdf_path: str,
        page_number: int,
        rect: Tuple[float, float, float, float],
        highlight_color: str = "yellow",
    ) -> str:
        """
        Render a zoomed screenshot of a bounding box on a given page and save it.

        A transparent highlight is added to draw attention to the matched text.
        Only a relative filename is returned; the file lives in `self.output_dir/screenshots`.
        """
        doc = fitz.open(pdf_path)
        try:
            page = doc[page_number - 1]
            # Highlight annotation
            annotation = page.add_highlight_annot(fitz.Rect(rect))
            annotation.set_colors(stroke=fitz.utils.getColor(highlight_color))
            annotation.update()
            # Expand capture box slightly for context
            x0, y0, x1, y1 = rect
            padding = 20
            clip = fitz.Rect(x0 - padding, y0 - padding, x1 + padding, y1 + padding)
            mat = fitz.Matrix(2, 2)  # 2× zoom for clarity
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{Path(pdf_path).stem}_p{page_number}_{timestamp}.png"
            out_path = self.output_dir / "screenshots" / filename
            pix.save(str(out_path))
            return filename
        finally:
            doc.close()

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def extract_by_template(
        self, pdf_path: str, template: Dict[str, Dict[str, Any]]
    ) -> List[ExtractedDataPoint]:
        """
        Scan a PDF for multiple fields defined by a template.

        The template should map field names to a dictionary with a `patterns` key
        containing a list of regular expressions.  The first (highest confidence)
        match for each field is returned.
        """
        doc = fitz.open(pdf_path)
        extractions: List[ExtractedDataPoint] = []
        try:
            for field_name, cfg in template.items():
                patterns = cfg.get("patterns", [])
                candidates: List[ExtractedDataPoint] = []
                for page_number, page in enumerate(doc, start=1):
                    text = page.get_text()
                    for pat in patterns:
                        # Precompile the regex; skip invalid expressions
                        try:
                            regex = re.compile(pat, re.IGNORECASE)
                        except re.error:
                            continue
                        for match in regex.finditer(text):
                            match_text = match.group(0)
                            # Determine the context around the match
                            start_idx = match.start()
                            start_context = max(0, start_idx - 100)
                            end_context = min(len(text), match.end() + 100)
                            context = text[start_context:end_context]
                            # Determine the on-page coordinates using search_for
                            instances = page.search_for(match_text)
                            if not instances:
                                continue
                            rect = instances[0]
                            # Derive the extracted value: capture group if available
                            if match.groups():
                                value = match.group(1)
                            else:
                                value = match_text
                            # Compute confidence and verification hash
                            confidence = self._compute_confidence(field_name, str(value), context)
                            ver_hash = self.create_verification_hash(
                                pdf_path, page_number, (rect.x0, rect.y0, rect.x1, rect.y1), match_text
                            )
                            # Optionally capture a screenshot for high‑confidence matches
                            screenshot = None
                            if confidence >= 0.7:
                                screenshot = self.capture_screenshot(
                                    pdf_path, page_number, (rect.x0, rect.y0, rect.x1, rect.y1)
                                )
                            extraction = ExtractedDataPoint(
                                field_name=field_name,
                                value=value,
                                page_number=page_number,
                                coordinates=(rect.x0, rect.y0, rect.x1, rect.y1),
                                context=context,
                                exact_text=match_text,
                                confidence=confidence,
                                extraction_method="regex",
                                timestamp=datetime.datetime.now().isoformat(),
                                verification_hash=ver_hash,
                                screenshot_path=screenshot,
                                source_type="text",
                            )
                            candidates.append(extraction)
                # Select the best candidate (highest confidence, then earliest page)
                if candidates:
                    candidates.sort(key=lambda e: (-e.confidence, e.page_number))
                    extractions.append(candidates[0])
        finally:
            doc.close()
        return extractions

    def highlight_pdf_with_extractions(
        self, pdf_path: str, extractions: List[ExtractedDataPoint]
    ) -> str:
        """
        Overlay colored highlights and inline notes for each extraction on the PDF.
        Returns the filename of the annotated PDF relative to the static output directory.
        """
        doc = fitz.open(pdf_path)
        try:
            # Group extractions by page
            by_page: Dict[int, List[ExtractedDataPoint]] = {}
            for ext in extractions:
                by_page.setdefault(ext.page_number, []).append(ext)
            for page_num, exts in by_page.items():
                page = doc[page_num - 1]
                for ext in exts:
                    # Choose highlight color based on confidence
                    if ext.confidence >= 0.9:
                        color = "green"
                    elif ext.confidence >= 0.7:
                        color = "yellow"
                    else:
                        color = "red"
                    highlight = page.add_highlight_annot(fitz.Rect(ext.coordinates))
                    highlight.set_colors(stroke=fitz.utils.getColor(color))
                    highlight.update()
                    # Add a small text annotation next to the highlight
                    point = fitz.Point(ext.coordinates[2] + 5, ext.coordinates[1])
                    note_text = f"{ext.field_name}: {ext.value} ({ext.confidence:.2f})"
                    annotation = page.add_text_annot(point, note_text)
                    annotation.set_info(title=f"{ext.field_name}")
                    annotation.update()
            filename = f"{Path(pdf_path).stem}_annotated.pdf"
            out_path = self.output_dir / "highlighted_pdfs" / filename
            doc.save(str(out_path))
            return filename
        finally:
            doc.close()

    def create_audit_report(
        self, pdf_path: str, extractions: List[ExtractedDataPoint]
    ) -> str:
        """
        Build a succinct audit report capturing key details of each extraction.
        """
        report = {
            "source_document": str(Path(pdf_path).resolve()),
            "generated_at": datetime.datetime.now().isoformat(),
            "extraction_count": len(extractions),
            "extractions": [],
        }
        for ext in extractions:
            report["extractions"].append(
                {
                    "field": ext.field_name,
                    "value": ext.value,
                    "page": ext.page_number,
                    "coordinates": ext.coordinates,
                    "confidence": ext.confidence,
                    "verification_hash": ext.verification_hash,
                    "screenshot": ext.screenshot_path,
                }
            )
        filename = (
            f"{Path(pdf_path).stem}_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        out_path = self.output_dir / "audit_logs" / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return filename

    def export_extractions_to_csv(
        self, extractions: List[ExtractedDataPoint]
    ) -> str:
        """
        Write all extractions to a CSV file and return the relative filename.
        """
        import pandas as pd

        rows = [ext.to_dict() for ext in extractions]
        df = pd.DataFrame(rows)
        filename = (
            f"extractions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        out_path = self.output_dir / "exports" / filename
        df.to_csv(out_path, index=False)
        return filename

    def export_extractions_to_jsonl(
        self, extractions: List[ExtractedDataPoint]
    ) -> str:
        """
        Write all extractions to a JSON Lines file and return the relative filename.
        """
        filename = (
            f"extractions_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        )
        out_path = self.output_dir / "exports" / filename
        with open(out_path, "w", encoding="utf-8") as f:
            for ext in extractions:
                f.write(json.dumps(ext.to_dict(), ensure_ascii=False) + "\n")
        return filename

    def extract_tables_with_location(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract tables from a PDF along with their bounding boxes and raw data.
        """
        doc = fitz.open(pdf_path)
        tables: List[Dict[str, Any]] = []
        try:
            for page_number, page in enumerate(doc, start=1):
                # `find_tables` may raise on scanned PDFs; ignore failures gracefully
                try:
                    found = page.find_tables()
                except Exception:
                    continue
                for idx, table in enumerate(found):
                    data = table.extract()
                    tables.append(
                        {
                            "page": page_number,
                            "table_index": idx,
                            "bbox": tuple(table.bbox),
                            "rows": len(data),
                            "cols": len(data[0]) if data else 0,
                            "data": data,
                        }
                    )
        finally:
            doc.close()
        return tables
