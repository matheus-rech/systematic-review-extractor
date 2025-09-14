"""Test configuration for pytest."""

import pytest
from pathlib import Path
from unittest.mock import Mock
import tempfile
import os

from systematic_review_extractor.models.schemas import ExtractionConfig


@pytest.fixture
def sample_config():
    """Provide a sample configuration for testing."""
    return ExtractionConfig(
        ai_provider="openai",
        model_name="gpt-4",
        max_tokens=1000,
        temperature=0.1,
        validation_enabled=True,
        confidence_threshold=0.7,
        retry_attempts=2
    )


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf_path(temp_dir):
    """Create a sample PDF file path (mock file)."""
    pdf_path = temp_dir / "sample_paper.pdf"
    # Create an empty file for testing (real PDF testing would require actual PDF files)
    pdf_path.touch()
    return pdf_path


@pytest.fixture
def sample_text():
    """Provide sample research paper text for testing."""
    return """
    Effectiveness of Exercise Interventions on Depression: A Systematic Review
    
    John Smith1, Jane Doe2, Bob Johnson1
    1University of Health Sciences, 2Research Institute
    
    Abstract
    Background: Depression is a major public health concern affecting millions worldwide.
    Methods: We conducted a systematic review of randomized controlled trials examining exercise interventions.
    Sample size: 1,245 participants across 15 studies.
    Results: Exercise interventions showed significant improvements in depression scores (p < 0.001).
    Conclusion: Regular exercise is an effective intervention for depression.
    
    Introduction
    Depression affects approximately 280 million people globally according to the WHO.
    
    Methods
    We searched PubMed, Cochrane Library, and PsycINFO databases.
    Inclusion criteria included randomized controlled trials published between 2010-2023.
    
    Results
    Primary outcome was measured using the Beck Depression Inventory.
    Mean improvement was 5.2 points (95% CI: 3.1-7.3, p = 0.001).
    """


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"field_name": "sample_size", "value": "1,245", "source_text": "Sample size: 1,245 participants", "confidence": 0.9}'
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = '{"field_name": "sample_size", "value": "1,245", "source_text": "Sample size: 1,245 participants", "confidence": 0.9}'
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    # Set test API keys to avoid warnings during testing
    os.environ.setdefault("OPENAI_API_KEY", "test-key")
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
    yield
    # Clean up is automatic as we're only setting defaults