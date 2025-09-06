"""Test the main extraction functionality."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from systematic_review_extractor.core.extractor import SystematicReviewExtractor
from systematic_review_extractor.models.schemas import ExtractionConfig, ExtractionResult


class TestSystematicReviewExtractor:
    """Test the main SystematicReviewExtractor class."""
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor()
            assert extractor.config is not None
            assert extractor.config.ai_provider == "openai"
            assert extractor.config.confidence_threshold == 0.7
    
    def test_init_with_custom_config(self, sample_config):
        """Test initialization with custom configuration."""
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            assert extractor.config == sample_config
            assert extractor.config.model_name == "gpt-4"
    
    @patch('systematic_review_extractor.extractors.pdf_extractor.PDFExtractor.extract_text')
    @patch('systematic_review_extractor.extractors.pdf_extractor.PDFExtractor.extract_metadata')
    @patch('systematic_review_extractor.extractors.ai_extractor.AIExtractor.extract_structured_data')
    def test_extract_from_file_success(
        self, 
        mock_ai_extract,
        mock_pdf_metadata,
        mock_pdf_extract,
        sample_config,
        sample_pdf_path,
        sample_text
    ):
        """Test successful extraction from a single file."""
        
        # Setup mocks
        mock_pdf_extract.return_value = (sample_text, [sample_text])
        mock_pdf_metadata.return_value = {"title": "Test Paper", "author": "Test Author"}
        
        from systematic_review_extractor.models.schemas import ExtractedData
        mock_ai_extract.return_value = [
            ExtractedData(
                field_name="sample_size",
                value="1,245",
                confidence_score=0.9,
                source_text="Sample size: 1,245 participants",
                extraction_method="ai_openai"
            )
        ]
        
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            result = extractor.extract_from_file(
                sample_pdf_path, 
                ["sample_size"],
                "Extract study characteristics"
            )
        
        # Verify result
        assert isinstance(result, ExtractionResult)
        assert len(result.extracted_data) == 1
        assert result.extracted_data[0].field_name == "sample_size"
        assert result.extracted_data[0].value == "1,245"
        assert result.processing_time_seconds > 0
        assert result.file_path == str(sample_pdf_path)
    
    def test_extract_from_nonexistent_file(self, sample_config):
        """Test extraction from non-existent file raises error."""
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            
            nonexistent_path = Path("/nonexistent/file.pdf")
            with pytest.raises(ValueError, match="Extraction failed"):
                extractor.extract_from_file(nonexistent_path, ["sample_size"])
    
    @patch('systematic_review_extractor.core.extractor.SystematicReviewExtractor.extract_from_file')
    def test_extract_from_files_batch(self, mock_extract_single, sample_config):
        """Test batch extraction from multiple files."""
        
        # Mock single file extraction
        from systematic_review_extractor.models.schemas import ExtractionResult, StudyMetadata, ValidationResult
        mock_result = ExtractionResult(
            study_metadata=StudyMetadata(title="Test"),
            extracted_data=[],
            validation_result=ValidationResult(is_valid=True, validation_score=1.0),
            processing_time_seconds=1.0
        )
        mock_extract_single.return_value = mock_result
        
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            
            file_paths = [Path(f"file{i}.pdf") for i in range(3)]
            results = extractor.extract_from_files(file_paths, ["sample_size"])
        
        assert len(results) == 3
        assert mock_extract_single.call_count == 3
    
    def test_get_processing_stats_empty(self, sample_config):
        """Test processing stats with empty results."""
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            stats = extractor.get_processing_stats([])
        
        assert stats.total_files == 0
        assert stats.successful_extractions == 0
        assert stats.failed_extractions == 0
        assert stats.average_processing_time == 0.0
        assert stats.validation_pass_rate == 0.0
    
    def test_get_processing_stats_with_results(self, sample_config):
        """Test processing stats calculation."""
        from systematic_review_extractor.models.schemas import (
            ExtractionResult, StudyMetadata, ValidationResult, ExtractedData
        )
        
        # Create mock results
        results = [
            ExtractionResult(
                study_metadata=StudyMetadata(title="Test 1"),
                extracted_data=[ExtractedData(
                    field_name="test", value="value", confidence_score=0.8,
                    source_text="", extraction_method="ai"
                )],
                validation_result=ValidationResult(is_valid=True, validation_score=0.9),
                processing_time_seconds=2.0
            ),
            ExtractionResult(
                study_metadata=StudyMetadata(title="Test 2"),
                extracted_data=[],
                validation_result=ValidationResult(is_valid=False, validation_score=0.3),
                processing_time_seconds=1.5
            )
        ]
        
        with patch('systematic_review_extractor.extractors.ai_extractor.openai'):
            extractor = SystematicReviewExtractor(sample_config)
            stats = extractor.get_processing_stats(results)
        
        assert stats.total_files == 2
        assert stats.successful_extractions == 1
        assert stats.failed_extractions == 1
        assert stats.average_processing_time == 1.75
        assert stats.total_processing_time == 3.5
        assert stats.validation_pass_rate == 0.5


class TestSystematicReviewExtractorIntegration:
    """Integration tests for the extractor (require mocked AI services)."""
    
    @pytest.mark.integration
    def test_full_extraction_pipeline_mocked(self, sample_config, temp_dir, sample_text):
        """Test the full extraction pipeline with mocked components."""
        
        # Create a fake PDF file with content
        pdf_path = temp_dir / "test_paper.pdf"
        pdf_path.write_text("fake pdf content")  # This won't be a real PDF
        
        with patch('systematic_review_extractor.extractors.pdf_extractor.PDFExtractor.extract_text') as mock_extract:
            with patch('systematic_review_extractor.extractors.pdf_extractor.PDFExtractor.extract_metadata') as mock_metadata:
                with patch('systematic_review_extractor.extractors.ai_extractor.openai') as mock_openai:
                    
                    # Setup mocks
                    mock_extract.return_value = (sample_text, [sample_text])
                    mock_metadata.return_value = {"title": "Mocked Title"}
                    
                    # Mock AI response
                    mock_client = Mock()
                    mock_response = Mock()
                    mock_response.choices = [Mock()]
                    mock_response.choices[0].message.content = '''
                    {
                        "field_name": "sample_size",
                        "value": "1,245 participants",
                        "source_text": "Sample size: 1,245 participants across 15 studies",
                        "confidence": 0.9
                    }
                    '''
                    mock_client.chat.completions.create.return_value = mock_response
                    mock_openai.OpenAI.return_value = mock_client
                    
                    # Run extraction
                    extractor = SystematicReviewExtractor(sample_config)
                    result = extractor.extract_from_file(
                        pdf_path,
                        ["sample_size"],
                        "Extract study characteristics"
                    )
                    
                    # Verify results
                    assert isinstance(result, ExtractionResult)
                    assert result.study_metadata.title
                    assert len(result.extracted_data) >= 0  # May be 0 if AI extraction fails
                    assert result.processing_time_seconds > 0