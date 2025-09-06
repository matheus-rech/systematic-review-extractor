"""
Enhanced HTTP API with AI capabilities, batch processing, and real-time updates.
"""

from __future__ import annotations

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import aiofiles

from ai_enhanced_extraction import AIEnhancedExtractionSystem, EnhancedExtraction


# Pydantic models for API
class ExtractionRequest(BaseModel):
    pdf_paths: List[str]
    template: Dict[str, Dict[str, Any]]
    use_llm: bool = True
    use_ocr: bool = False
    use_medical_agents: bool = True
    batch_size: int = 5


class ExtractionStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: float
    total_pdfs: int
    completed_pdfs: int
    results: Optional[Dict] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FeedbackRequest(BaseModel):
    extraction_id: str
    field_name: str
    decision: str  # verified, flagged, rejected
    notes: str = ""


class TemplateGenerationRequest(BaseModel):
    sample_pdfs: List[str]
    domain: str = "medical"  # medical, social_sciences, engineering, etc.


# Initialize FastAPI app
app = FastAPI(
    title="AI-Enhanced Systematic Review Extraction API",
    version="2.0.0",
    description="Advanced PDF extraction with AI/ML capabilities"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize extraction system
system = AIEnhancedExtractionSystem(
    anthropic_api_key=None,  # Will use env variable
    use_medical_agents=True
)

# Job tracking
extraction_jobs: Dict[str, ExtractionStatus] = {}

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=system.output_dir, html=True),
    name="static",
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time extraction updates."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def process_extraction_job(
    job_id: str,
    pdf_paths: List[str],
    template: Dict[str, Dict[str, Any]],
    use_llm: bool,
    use_ocr: bool
):
    """Background task for processing extractions."""
    try:
        job = extraction_jobs[job_id]
        job.status = "processing"
        job.updated_at = datetime.now()
        
        # Broadcast update
        await manager.broadcast({
            "job_id": job_id,
            "status": "processing",
            "message": f"Starting extraction of {len(pdf_paths)} PDFs"
        })
        
        results = {}
        for i, pdf_path in enumerate(pdf_paths):
            # Update progress
            job.completed_pdfs = i
            job.progress = (i / len(pdf_paths)) * 100
            job.updated_at = datetime.now()
            
            # Broadcast progress
            await manager.broadcast({
                "job_id": job_id,
                "progress": job.progress,
                "current_pdf": pdf_path
            })
            
            # Process PDF
            extractions = await system.extract_by_template_enhanced(
                pdf_path, template, use_llm=use_llm, use_ocr=use_ocr
            )
            
            # Convert to dict
            results[pdf_path] = [e.to_dict() for e in extractions]
            
            # Generate artifacts
            system.highlight_pdf_with_extractions(pdf_path, extractions)
            system.create_audit_report(pdf_path, extractions)
        
        # Complete job
        job.status = "completed"
        job.progress = 100
        job.completed_pdfs = len(pdf_paths)
        job.results = results
        job.updated_at = datetime.now()
        
        # Broadcast completion
        await manager.broadcast({
            "job_id": job_id,
            "status": "completed",
            "message": f"Successfully extracted from {len(pdf_paths)} PDFs"
        })
        
    except Exception as e:
        logger.error(f"Extraction job {job_id} failed: {e}")
        job = extraction_jobs[job_id]
        job.status = "failed"
        job.error = str(e)
        job.updated_at = datetime.now()
        
        # Broadcast error
        await manager.broadcast({
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        })


@app.post("/api/v2/extract/batch")
async def batch_extract_async(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit batch extraction job for async processing.
    """
    # Create job
    job_id = str(uuid.uuid4())
    job = ExtractionStatus(
        job_id=job_id,
        status="pending",
        progress=0,
        total_pdfs=len(request.pdf_paths),
        completed_pdfs=0,
        results=None,
        error=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    extraction_jobs[job_id] = job
    
    # Start background processing
    background_tasks.add_task(
        process_extraction_job,
        job_id,
        request.pdf_paths,
        request.template,
        request.use_llm,
        request.use_ocr
    )
    
    return {"job_id": job_id, "status": "pending"}


@app.get("/api/v2/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of extraction job."""
    if job_id not in extraction_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = extraction_jobs[job_id]
    return job.dict()


@app.post("/api/v2/extract/single")
async def extract_single_enhanced(
    pdf_file: UploadFile = File(...),
    template_file: UploadFile = File(...),
    use_llm: bool = True,
    use_ocr: bool = False
):
    """
    Enhanced single PDF extraction with AI capabilities.
    """
    # Save uploaded PDF
    uploads_dir = system.output_dir / "uploads"
    pdf_path = uploads_dir / pdf_file.filename
    
    async with aiofiles.open(pdf_path, "wb") as f:
        content = await pdf_file.read()
        await f.write(content)
    
    # Parse template
    try:
        template_content = await template_file.read()
        template = json.loads(template_content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid template: {e}")
    
    # Perform enhanced extraction
    try:
        extractions = await system.extract_by_template_enhanced(
            str(pdf_path), template, use_llm=use_llm, use_ocr=use_ocr
        )
        
        # Generate artifacts
        annotated_pdf = system.highlight_pdf_with_extractions(str(pdf_path), extractions)
        audit_log = system.create_audit_report(str(pdf_path), extractions)
        csv_file = system.export_extractions_to_csv(extractions)
        jsonl_file = system.export_extractions_to_jsonl(extractions)
        
        # Build response
        return JSONResponse({
            "extractions": [e.to_dict() for e in extractions],
            "annotated_pdf": annotated_pdf,
            "audit_log": audit_log,
            "csv": csv_file,
            "jsonl": jsonl_file,
            "statistics": {
                "total_fields": len(template),
                "extracted_fields": len(extractions),
                "llm_validated": sum(1 for e in extractions if hasattr(e, 'llm_validated') and e.llm_validated),
                "avg_confidence": sum(e.confidence for e in extractions) / len(extractions) if extractions else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback for an extraction to improve the system.
    """
    # This would look up the extraction and update it
    # For now, just log it
    logger.info(f"Feedback received: {feedback.dict()}")
    
    # In production, this would:
    # 1. Update the extraction in the database
    # 2. Retrain confidence models
    # 3. Update vector embeddings
    
    return {"status": "feedback_received"}


@app.post("/api/v2/template/generate")
async def generate_template(request: TemplateGenerationRequest):
    """
    Generate extraction template based on sample PDFs and domain.
    """
    template = system.generate_smart_template(request.sample_pdfs)
    
    # Customize for domain
    if request.domain == "medical":
        template.update({
            "clinical_trial_phase": {
                "patterns": [r"phase\s+([IVX]+|\d+)", r"([IVX]+|\d+)\s+trial"],
                "hint": "Clinical trial phase",
                "required": False,
                "type": "string"
            },
            "adverse_events": {
                "patterns": [r"adverse\s+events?[:\s]+([^.]+)", r"AE[:\s]+([^.]+)"],
                "hint": "Adverse events reported",
                "required": False,
                "type": "string"
            }
        })
    elif request.domain == "social_sciences":
        template.update({
            "methodology": {
                "patterns": [r"methodology[:\s]+([^.]+)", r"methods?[:\s]+([^.]+)"],
                "hint": "Research methodology",
                "required": True,
                "type": "string"
            },
            "theoretical_framework": {
                "patterns": [r"framework[:\s]+([^.]+)", r"theory[:\s]+([^.]+)"],
                "hint": "Theoretical framework",
                "required": False,
                "type": "string"
            }
        })
    
    return template


@app.get("/api/v2/templates/library")
async def get_template_library():
    """
    Get pre-built templates for common systematic review types.
    """
    return {
        "medical_rct": {
            "name": "Medical RCT",
            "description": "Template for randomized controlled trials",
            "template": system.generate_smart_template([])
        },
        "meta_analysis": {
            "name": "Meta-Analysis",
            "description": "Template for meta-analysis studies",
            "template": {
                "study_id": {"patterns": [r"study\s+(\w+)"], "hint": "Study identifier", "required": True, "type": "string"},
                "sample_size": {"patterns": [r"n\s*=\s*(\d+)"], "hint": "Sample size", "required": True, "type": "integer"},
                "effect_size": {"patterns": [r"d\s*=\s*([\d.-]+)"], "hint": "Effect size", "required": True, "type": "float"},
                "confidence_interval": {"patterns": [r"CI[:\s]+\[([\d.-]+)[,\s]+([\d.-]+)\]"], "hint": "95% CI", "required": True, "type": "string"},
                "heterogeneity": {"patterns": [r"I2\s*=\s*([\d.]+)%?"], "hint": "I-squared", "required": False, "type": "float"}
            }
        },
        "qualitative": {
            "name": "Qualitative Study",
            "description": "Template for qualitative research",
            "template": {
                "methodology": {"patterns": [r"methodology[:\s]+([^.]+)"], "hint": "Methodology", "required": True, "type": "string"},
                "sample_size": {"patterns": [r"(\d+)\s*participants?"], "hint": "Number of participants", "required": True, "type": "integer"},
                "themes": {"patterns": [r"themes?[:\s]+([^.]+)"], "hint": "Main themes", "required": True, "type": "string"},
                "data_collection": {"patterns": [r"data\s+collection[:\s]+([^.]+)"], "hint": "Data collection method", "required": True, "type": "string"}
            }
        }
    }


@app.get("/api/v2/statistics")
async def get_extraction_statistics():
    """
    Get system statistics and performance metrics.
    """
    # Calculate statistics from vector store
    collection_stats = system.collection.count()
    
    return {
        "total_extractions": collection_stats,
        "active_jobs": len([j for j in extraction_jobs.values() if j.status == "processing"]),
        "completed_jobs": len([j for j in extraction_jobs.values() if j.status == "completed"]),
        "failed_jobs": len([j for j in extraction_jobs.values() if j.status == "failed"]),
        "vector_store_size": collection_stats,
        "models_available": {
            "llm": system.claude is not None,
            "medical_agents": system.medical_agent is not None,
            "nlp": system.nlp is not None,
            "confidence_model": system.confidence_model is not None
        }
    }


@app.post("/api/v2/search/similar")
async def search_similar_extractions(
    field_name: str,
    value: str,
    limit: int = 10
):
    """
    Search for similar extractions in the vector store.
    """
    from verified_extraction_system import ExtractedDataPoint
    
    # Create a dummy extraction for similarity search
    dummy = ExtractedDataPoint(
        field_name=field_name,
        value=value,
        page_number=1,
        coordinates=(0, 0, 0, 0),
        context="",
        exact_text=value,
        confidence=0,
        extraction_method="search",
        timestamp=datetime.now().isoformat(),
        verification_hash=""
    )
    
    similar = system.find_similar_extractions(dummy, n_results=limit)
    
    return {"similar_extractions": similar}


@app.get("/api/v2/health")
async def health_check():
    """
    Health check endpoint with system status.
    """
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "ai_extraction": True,
            "llm_validation": system.claude is not None,
            "medical_agents": system.medical_agent is not None,
            "ocr": True,
            "vector_search": True,
            "batch_processing": True,
            "websocket_updates": True
        },
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.app(app, host="0.0.0.0", port=8000, reload=True)