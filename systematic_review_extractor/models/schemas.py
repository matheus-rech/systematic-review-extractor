"""Data models and schemas for systematic review extraction."""

from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class Author(BaseModel):
    """Author information."""
    name: str = Field(..., description="Full name of the author")
    affiliation: Optional[str] = Field(None, description="Author's institutional affiliation")
    email: Optional[str] = Field(None, description="Author's email address")


class StudyMetadata(BaseModel):
    """Metadata for a research study."""
    title: str = Field(..., description="Study title")
    authors: List[Author] = Field(default_factory=list, description="List of study authors")
    publication_year: Optional[int] = Field(None, description="Year of publication")
    journal: Optional[str] = Field(None, description="Journal name")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    abstract: Optional[str] = Field(None, description="Study abstract")
    keywords: List[str] = Field(default_factory=list, description="Study keywords")
    study_type: Optional[str] = Field(None, description="Type of study (e.g., RCT, cohort, etc.)")


class ExtractionCriteria(BaseModel):
    """Criteria for data extraction."""
    fields_to_extract: List[str] = Field(..., description="List of fields to extract from studies")
    inclusion_criteria: List[str] = Field(default_factory=list, description="Study inclusion criteria")
    exclusion_criteria: List[str] = Field(default_factory=list, description="Study exclusion criteria")
    quality_thresholds: Dict[str, Any] = Field(default_factory=dict, description="Quality assessment thresholds")


class ExtractedData(BaseModel):
    """Extracted data from a study."""
    field_name: str = Field(..., description="Name of the extracted field")
    value: Any = Field(..., description="Extracted value")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in extraction (0-1)")
    source_text: str = Field(..., description="Source text from which the value was extracted")
    page_number: Optional[int] = Field(None, description="Page number where the data was found")
    extraction_method: str = Field(..., description="Method used for extraction (e.g., 'ai', 'regex', 'manual')")


class ValidationResult(BaseModel):
    """Result of data validation."""
    is_valid: bool = Field(..., description="Whether the extracted data is valid")
    validation_score: float = Field(..., ge=0.0, le=1.0, description="Validation confidence score")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")


class ExtractionResult(BaseModel):
    """Complete result of data extraction from a study."""
    study_metadata: StudyMetadata = Field(..., description="Study metadata")
    extracted_data: List[ExtractedData] = Field(default_factory=list, description="Extracted data points")
    validation_result: ValidationResult = Field(..., description="Validation results")
    extraction_timestamp: datetime = Field(default_factory=datetime.now, description="When extraction was performed")
    processing_time_seconds: float = Field(..., description="Time taken for extraction in seconds")
    file_path: Optional[str] = Field(None, description="Path to the source file")
    
    @field_validator('processing_time_seconds')
    @classmethod
    def validate_processing_time(cls, v):
        if v < 0:
            raise ValueError('Processing time must be non-negative')
        return v


class ExtractionConfig(BaseModel):
    """Configuration for the extraction process."""
    ai_provider: Literal["openai", "anthropic"] = Field(default="openai", description="AI provider to use")
    model_name: str = Field(default="gpt-4", description="AI model name")
    max_tokens: int = Field(default=4000, description="Maximum tokens for AI responses")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="AI temperature setting")
    validation_enabled: bool = Field(default=True, description="Whether to enable validation")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence threshold")
    retry_attempts: int = Field(default=3, ge=1, description="Number of retry attempts for failed extractions")


class ProcessingStats(BaseModel):
    """Statistics for a processing session."""
    total_files: int = Field(..., description="Total number of files processed")
    successful_extractions: int = Field(..., description="Number of successful extractions")
    failed_extractions: int = Field(..., description="Number of failed extractions")
    average_processing_time: float = Field(..., description="Average processing time per file")
    total_processing_time: float = Field(..., description="Total processing time")
    validation_pass_rate: float = Field(..., ge=0.0, le=1.0, description="Percentage of extractions that passed validation")