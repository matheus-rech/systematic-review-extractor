"""Test the data models and schemas."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from systematic_review_extractor.models.schemas import (
    Author,
    StudyMetadata,
    ExtractedData,
    ExtractionResult,
    ExtractionConfig,
    ValidationResult,
    ProcessingStats
)


class TestAuthor:
    """Test Author model."""
    
    def test_author_creation_minimal(self):
        """Test creating author with minimal information."""
        author = Author(name="John Doe")
        assert author.name == "John Doe"
        assert author.affiliation is None
        assert author.email is None
    
    def test_author_creation_full(self):
        """Test creating author with full information."""
        author = Author(
            name="Jane Smith",
            affiliation="University of Science",
            email="jane.smith@university.edu"
        )
        assert author.name == "Jane Smith"
        assert author.affiliation == "University of Science"
        assert author.email == "jane.smith@university.edu"
    
    def test_author_name_required(self):
        """Test that author name is required."""
        with pytest.raises(ValidationError):
            Author()


class TestStudyMetadata:
    """Test StudyMetadata model."""
    
    def test_study_metadata_minimal(self):
        """Test creating study metadata with minimal information."""
        metadata = StudyMetadata(title="Test Study")
        assert metadata.title == "Test Study"
        assert metadata.authors == []
        assert metadata.publication_year is None
    
    def test_study_metadata_full(self):
        """Test creating study metadata with full information."""
        authors = [Author(name="John Doe"), Author(name="Jane Smith")]
        metadata = StudyMetadata(
            title="Comprehensive Study",
            authors=authors,
            publication_year=2023,
            journal="Journal of Science",
            doi="10.1000/test",
            abstract="This is a test abstract",
            keywords=["test", "science"],
            study_type="randomized controlled trial"
        )
        
        assert metadata.title == "Comprehensive Study"
        assert len(metadata.authors) == 2
        assert metadata.publication_year == 2023
        assert metadata.journal == "Journal of Science"
        assert metadata.doi == "10.1000/test"
        assert "test" in metadata.keywords


class TestExtractedData:
    """Test ExtractedData model."""
    
    def test_extracted_data_creation(self):
        """Test creating extracted data."""
        data = ExtractedData(
            field_name="sample_size",
            value="100 participants",
            confidence_score=0.85,
            source_text="The study included 100 participants",
            extraction_method="ai_openai"
        )
        
        assert data.field_name == "sample_size"
        assert data.value == "100 participants"
        assert data.confidence_score == 0.85
        assert data.source_text == "The study included 100 participants"
        assert data.extraction_method == "ai_openai"
        assert data.page_number is None
    
    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid confidence scores
        ExtractedData(
            field_name="test",
            value="value",
            confidence_score=0.0,
            source_text="source",
            extraction_method="method"
        )
        
        ExtractedData(
            field_name="test",
            value="value", 
            confidence_score=1.0,
            source_text="source",
            extraction_method="method"
        )
        
        # Invalid confidence scores
        with pytest.raises(ValidationError):
            ExtractedData(
                field_name="test",
                value="value",
                confidence_score=-0.1,
                source_text="source",
                extraction_method="method"
            )
        
        with pytest.raises(ValidationError):
            ExtractedData(
                field_name="test",
                value="value",
                confidence_score=1.1,
                source_text="source",
                extraction_method="method"
            )


class TestValidationResult:
    """Test ValidationResult model."""
    
    def test_validation_result_success(self):
        """Test successful validation result."""
        result = ValidationResult(
            is_valid=True,
            validation_score=0.95,
            errors=[],
            warnings=["Minor warning"]
        )
        
        assert result.is_valid is True
        assert result.validation_score == 0.95
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
    
    def test_validation_result_failure(self):
        """Test failed validation result."""
        result = ValidationResult(
            is_valid=False,
            validation_score=0.3,
            errors=["Critical error", "Another error"],
            warnings=[]
        )
        
        assert result.is_valid is False
        assert result.validation_score == 0.3
        assert len(result.errors) == 2
        assert len(result.warnings) == 0


class TestExtractionResult:
    """Test ExtractionResult model."""
    
    def test_extraction_result_creation(self):
        """Test creating extraction result."""
        metadata = StudyMetadata(title="Test Study")
        validation = ValidationResult(is_valid=True, validation_score=0.9)
        
        result = ExtractionResult(
            study_metadata=metadata,
            extracted_data=[],
            validation_result=validation,
            processing_time_seconds=5.5
        )
        
        assert result.study_metadata.title == "Test Study"
        assert len(result.extracted_data) == 0
        assert result.validation_result.is_valid is True
        assert result.processing_time_seconds == 5.5
        assert isinstance(result.extraction_timestamp, datetime)
    
    def test_processing_time_validation(self):
        """Test processing time validation."""
        metadata = StudyMetadata(title="Test")
        validation = ValidationResult(is_valid=True, validation_score=0.9)
        
        # Valid processing time
        ExtractionResult(
            study_metadata=metadata,
            validation_result=validation,
            processing_time_seconds=0.0
        )
        
        # Invalid processing time
        with pytest.raises(ValidationError):
            ExtractionResult(
                study_metadata=metadata,
                validation_result=validation,
                processing_time_seconds=-1.0
            )


class TestExtractionConfig:
    """Test ExtractionConfig model."""
    
    def test_config_defaults(self):
        """Test default configuration values."""
        config = ExtractionConfig()
        
        assert config.ai_provider == "openai"
        assert config.model_name == "gpt-4"
        assert config.max_tokens == 4000
        assert config.temperature == 0.1
        assert config.validation_enabled is True
        assert config.confidence_threshold == 0.7
        assert config.retry_attempts == 3
    
    def test_config_custom_values(self):
        """Test configuration with custom values."""
        config = ExtractionConfig(
            ai_provider="anthropic",
            model_name="claude-3-sonnet",
            max_tokens=2000,
            temperature=0.0,
            validation_enabled=False,
            confidence_threshold=0.8,
            retry_attempts=1
        )
        
        assert config.ai_provider == "anthropic"
        assert config.model_name == "claude-3-sonnet"
        assert config.max_tokens == 2000
        assert config.temperature == 0.0
        assert config.validation_enabled is False
        assert config.confidence_threshold == 0.8
        assert config.retry_attempts == 1
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid temperature range
        ExtractionConfig(temperature=0.0)
        ExtractionConfig(temperature=2.0)
        
        # Invalid temperature
        with pytest.raises(ValidationError):
            ExtractionConfig(temperature=-0.1)
        
        with pytest.raises(ValidationError):
            ExtractionConfig(temperature=2.1)
        
        # Valid confidence threshold
        ExtractionConfig(confidence_threshold=0.0)
        ExtractionConfig(confidence_threshold=1.0)
        
        # Invalid confidence threshold
        with pytest.raises(ValidationError):
            ExtractionConfig(confidence_threshold=-0.1)
        
        with pytest.raises(ValidationError):
            ExtractionConfig(confidence_threshold=1.1)
        
        # Valid retry attempts
        ExtractionConfig(retry_attempts=1)
        
        # Invalid retry attempts
        with pytest.raises(ValidationError):
            ExtractionConfig(retry_attempts=0)


class TestProcessingStats:
    """Test ProcessingStats model."""
    
    def test_processing_stats_creation(self):
        """Test creating processing statistics."""
        stats = ProcessingStats(
            total_files=10,
            successful_extractions=8,
            failed_extractions=2,
            average_processing_time=2.5,
            total_processing_time=25.0,
            validation_pass_rate=0.8
        )
        
        assert stats.total_files == 10
        assert stats.successful_extractions == 8
        assert stats.failed_extractions == 2
        assert stats.average_processing_time == 2.5
        assert stats.total_processing_time == 25.0
        assert stats.validation_pass_rate == 0.8
    
    def test_validation_pass_rate_bounds(self):
        """Test validation pass rate bounds."""
        # Valid rates
        ProcessingStats(
            total_files=1,
            successful_extractions=1,
            failed_extractions=0,
            average_processing_time=1.0,
            total_processing_time=1.0,
            validation_pass_rate=0.0
        )
        
        ProcessingStats(
            total_files=1,
            successful_extractions=1,
            failed_extractions=0,
            average_processing_time=1.0,
            total_processing_time=1.0,
            validation_pass_rate=1.0
        )
        
        # Invalid rates
        with pytest.raises(ValidationError):
            ProcessingStats(
                total_files=1,
                successful_extractions=1,
                failed_extractions=0,
                average_processing_time=1.0,
                total_processing_time=1.0,
                validation_pass_rate=-0.1
            )
        
        with pytest.raises(ValidationError):
            ProcessingStats(
                total_files=1,
                successful_extractions=1,
                failed_extractions=0,
                average_processing_time=1.0,
                total_processing_time=1.0,
                validation_pass_rate=1.1
            )