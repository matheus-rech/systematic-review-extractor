"""
Database models and operations for persistent storage.
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional, Dict, Any
import os
from loguru import logger

Base = declarative_base()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/systematic_review")
# For SQLite (simpler setup): 
# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./systematic_review.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Project(Base):
    """Systematic review project."""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    settings = Column(JSON)  # Project-specific settings
    
    # Relationships
    pdfs = relationship("PDF", back_populates="project", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="project", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="project")


class PDF(Base):
    """PDF document."""
    __tablename__ = "pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True)  # For duplicate detection
    page_count = Column(Integer)
    is_scanned = Column(Boolean, default=False)
    metadata = Column(JSON)  # Store PDF metadata
    uploaded_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    
    # Relationships
    project = relationship("Project", back_populates="pdfs")
    extractions = relationship("Extraction", back_populates="pdf", cascade="all, delete-orphan")


class Template(Base):
    """Extraction template."""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    domain = Column(String)  # medical, social_sciences, etc.
    fields = Column(JSON, nullable=False)  # Template JSON structure
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String)
    
    # Relationships
    project = relationship("Project", back_populates="templates")
    extractions = relationship("Extraction", back_populates="template")


class Extraction(Base):
    """Extracted data point."""
    __tablename__ = "extractions"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    pdf_id = Column(Integer, ForeignKey("pdfs.id"))
    template_id = Column(Integer, ForeignKey("templates.id"))
    job_id = Column(String, index=True)  # Batch job ID
    
    # Extraction data
    field_name = Column(String, nullable=False, index=True)
    value = Column(Text)
    value_type = Column(String)  # integer, float, string, etc.
    page_number = Column(Integer)
    coordinates = Column(JSON)  # [x0, y0, x1, y1]
    context = Column(Text)
    exact_text = Column(Text)
    
    # Confidence and validation
    confidence = Column(Float)
    extraction_method = Column(String)  # regex, llm_claude, ocr, etc.
    llm_validated = Column(Boolean, default=False)
    llm_confidence = Column(Float)
    llm_explanation = Column(Text)
    
    # Review status
    status = Column(String, default="pending", index=True)  # pending, verified, flagged, rejected
    reviewer_notes = Column(Text)
    reviewed_by = Column(String)
    reviewed_at = Column(DateTime)
    
    # Metadata
    verification_hash = Column(String, index=True)
    screenshot_path = Column(String)
    embedding_id = Column(String)  # Vector store ID
    similar_extractions = Column(JSON)  # IDs of similar extractions
    
    # Timestamps
    extracted_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="extractions")
    pdf = relationship("PDF", back_populates="extractions")
    template = relationship("Template", back_populates="extractions")
    feedback_history = relationship("Feedback", back_populates="extraction", cascade="all, delete-orphan")


class Feedback(Base):
    """User feedback on extractions."""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    extraction_id = Column(Integer, ForeignKey("extractions.id"))
    decision = Column(String, nullable=False)  # verified, flagged, rejected
    notes = Column(Text)
    confidence_adjustment = Column(Float)  # How much to adjust confidence
    created_by = Column(String)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    extraction = relationship("Extraction", back_populates="feedback_history")


class Job(Base):
    """Batch extraction job."""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    status = Column(String, default="pending")  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)
    total_pdfs = Column(Integer)
    completed_pdfs = Column(Integer, default=0)
    template_id = Column(Integer, ForeignKey("templates.id"))
    settings = Column(JSON)  # Job-specific settings (use_llm, use_ocr, etc.)
    results = Column(JSON)  # Summary of results
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_by = Column(String)


# Database operations
class DatabaseOperations:
    """Database operations wrapper."""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized")
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def create_project(self, name: str, description: str = None) -> Project:
        """Create a new project."""
        with self.get_session() as session:
            project = Project(name=name, description=description)
            session.add(project)
            session.commit()
            session.refresh(project)
            logger.info(f"Created project: {project.id}")
            return project
    
    def add_pdf(self, project_id: int, filename: str, file_path: str, file_hash: str) -> PDF:
        """Add a PDF to a project."""
        with self.get_session() as session:
            # Check for duplicates
            existing = session.query(PDF).filter_by(file_hash=file_hash, project_id=project_id).first()
            if existing:
                logger.warning(f"PDF already exists: {filename}")
                return existing
            
            pdf = PDF(
                project_id=project_id,
                filename=filename,
                file_path=file_path,
                file_hash=file_hash
            )
            session.add(pdf)
            session.commit()
            session.refresh(pdf)
            logger.info(f"Added PDF: {pdf.id}")
            return pdf
    
    def save_extraction(self, extraction_data: Dict[str, Any]) -> Extraction:
        """Save an extraction to the database."""
        with self.get_session() as session:
            extraction = Extraction(**extraction_data)
            session.add(extraction)
            session.commit()
            session.refresh(extraction)
            return extraction
    
    def bulk_save_extractions(self, extractions: List[Dict[str, Any]]) -> List[Extraction]:
        """Save multiple extractions efficiently."""
        with self.get_session() as session:
            extraction_objects = [Extraction(**data) for data in extractions]
            session.bulk_save_objects(extraction_objects)
            session.commit()
            logger.info(f"Saved {len(extractions)} extractions")
            return extraction_objects
    
    def update_extraction_status(
        self,
        extraction_id: int,
        status: str,
        notes: str = None,
        reviewer: str = None
    ) -> Extraction:
        """Update extraction review status."""
        with self.get_session() as session:
            extraction = session.query(Extraction).filter_by(id=extraction_id).first()
            if extraction:
                extraction.status = status
                extraction.reviewer_notes = notes
                extraction.reviewed_by = reviewer
                extraction.reviewed_at = datetime.now()
                session.commit()
                session.refresh(extraction)
                
                # Add to feedback history
                feedback = Feedback(
                    extraction_id=extraction_id,
                    decision=status,
                    notes=notes,
                    created_by=reviewer
                )
                session.add(feedback)
                session.commit()
                
            return extraction
    
    def get_project_statistics(self, project_id: int) -> Dict[str, Any]:
        """Get project statistics."""
        with self.get_session() as session:
            total_pdfs = session.query(PDF).filter_by(project_id=project_id).count()
            processed_pdfs = session.query(PDF).filter_by(
                project_id=project_id,
                status="completed"
            ).count()
            
            total_extractions = session.query(Extraction).filter_by(project_id=project_id).count()
            
            status_counts = {}
            for status in ["pending", "verified", "flagged", "rejected"]:
                count = session.query(Extraction).filter_by(
                    project_id=project_id,
                    status=status
                ).count()
                status_counts[status] = count
            
            avg_confidence = session.query(func.avg(Extraction.confidence)).filter_by(
                project_id=project_id
            ).scalar() or 0
            
            return {
                "total_pdfs": total_pdfs,
                "processed_pdfs": processed_pdfs,
                "total_extractions": total_extractions,
                "status_counts": status_counts,
                "average_confidence": float(avg_confidence),
                "completion_rate": (status_counts["verified"] / total_extractions * 100) if total_extractions > 0 else 0
            }
    
    def search_extractions(
        self,
        project_id: int = None,
        field_name: str = None,
        value_contains: str = None,
        status: str = None,
        min_confidence: float = None,
        limit: int = 100
    ) -> List[Extraction]:
        """Search extractions with filters."""
        with self.get_session() as session:
            query = session.query(Extraction)
            
            if project_id:
                query = query.filter_by(project_id=project_id)
            if field_name:
                query = query.filter_by(field_name=field_name)
            if value_contains:
                query = query.filter(Extraction.value.contains(value_contains))
            if status:
                query = query.filter_by(status=status)
            if min_confidence:
                query = query.filter(Extraction.confidence >= min_confidence)
            
            return query.limit(limit).all()
    
    def get_extraction_history(self, extraction_id: int) -> List[Feedback]:
        """Get feedback history for an extraction."""
        with self.get_session() as session:
            return session.query(Feedback).filter_by(
                extraction_id=extraction_id
            ).order_by(Feedback.created_at.desc()).all()
    
    def cleanup_old_jobs(self, days: int = 30):
        """Clean up old completed jobs."""
        with self.get_session() as session:
            cutoff_date = datetime.now() - timedelta(days=days)
            old_jobs = session.query(Job).filter(
                Job.completed_at < cutoff_date,
                Job.status.in_(["completed", "failed"])
            ).all()
            
            for job in old_jobs:
                session.delete(job)
            
            session.commit()
            logger.info(f"Cleaned up {len(old_jobs)} old jobs")


# Initialize database operations
db_ops = DatabaseOperations()


# Example usage
if __name__ == "__main__":
    from datetime import timedelta
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Test operations
    project = db_ops.create_project(
        name="COVID-19 Treatment Meta-Analysis",
        description="Systematic review of COVID-19 treatments"
    )
    
    pdf = db_ops.add_pdf(
        project_id=project.id,
        filename="study1.pdf",
        file_path="/uploads/study1.pdf",
        file_hash="abc123"
    )
    
    extraction = db_ops.save_extraction({
        "project_id": project.id,
        "pdf_id": pdf.id,
        "field_name": "sample_size",
        "value": "150",
        "page_number": 5,
        "confidence": 0.92
    })
    
    stats = db_ops.get_project_statistics(project.id)
    print(f"Project statistics: {stats}")
    
    logger.info("Database test completed successfully")