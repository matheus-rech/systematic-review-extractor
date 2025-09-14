"""Models package for systematic review extractor."""

from .schemas import (
    Author,
    StudyMetadata,
    ExtractionCriteria,
    ExtractedData,
    ValidationResult,
    ExtractionResult,
    ExtractionConfig,
    ProcessingStats,
)

__all__ = [
    "Author",
    "StudyMetadata", 
    "ExtractionCriteria",
    "ExtractedData",
    "ValidationResult",
    "ExtractionResult",
    "ExtractionConfig",
    "ProcessingStats",
]