"""
Systematic Review Extractor

AI-powered systematic review data extraction system with zero hallucination guarantee.
This package provides tools for extracting structured data from research papers
and systematic reviews while ensuring accuracy and preventing AI hallucinations.
"""

__version__ = "0.1.0"
__author__ = "Matheus Rech"
__email__ = "matheus@example.com"

from .core.extractor import SystematicReviewExtractor
from .models.schemas import ExtractionResult, StudyMetadata

__all__ = [
    "SystematicReviewExtractor",
    "ExtractionResult", 
    "StudyMetadata",
]