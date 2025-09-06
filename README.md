# Systematic Review Extractor

AI-powered systematic review data extraction system with zero hallucination guarantee. This tool helps researchers extract structured data from research papers and systematic reviews while ensuring accuracy and preventing AI hallucinations through validation and verification mechanisms.

## Features

- **Zero Hallucination Guarantee**: Advanced validation system to prevent AI from generating false information
- **Multiple AI Providers**: Support for OpenAI GPT models and Anthropic Claude
- **PDF Text Extraction**: Robust PDF processing with text cleaning and section detection
- **Structured Data Output**: Export results in JSON, CSV, or Excel formats
- **Validation Framework**: Multi-level validation to ensure data accuracy
- **Batch Processing**: Process multiple PDF files efficiently
- **CLI Interface**: Easy-to-use command-line interface
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Installation

### Prerequisites

- Python 3.8 or higher
- API key for OpenAI or Anthropic

### Install from Source

```bash
git clone https://github.com/matheus-rech/systematic-review-extractor.git
cd systematic-review-extractor
pip install -e .
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

## Quick Start

### 1. Initialize Configuration

```bash
sr-extract init
```

This creates a `.env` file. Edit it and add your API keys:

```env
# AI Provider Settings
AI_PROVIDER=openai
MODEL_NAME=gpt-4
OPENAI_API_KEY=your_openai_api_key_here

# Or for Anthropic
# AI_PROVIDER=anthropic
# MODEL_NAME=claude-3-sonnet-20240229
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Extraction Settings
CONFIDENCE_THRESHOLD=0.7
VALIDATION_ENABLED=true
```

### 2. Extract Data from PDFs

Extract specific fields from a single PDF:
```bash
sr-extract extract paper.pdf --fields sample_size --fields study_design --fields primary_outcome
```

Process multiple PDFs in a directory:
```bash
sr-extract extract /path/to/papers/ --fields intervention --fields population --fields results
```

Export to different formats:
```bash
# JSON (default)
sr-extract extract papers/ --fields sample_size --output results.json

# CSV
sr-extract extract papers/ --fields sample_size --format csv --output results.csv

# Excel
sr-extract extract papers/ --fields sample_size --format excel --output results.xlsx
```

### 3. Validate Configuration

```bash
sr-extract validate-config
```

## Usage Examples

### Python API

```python
from pathlib import Path
from systematic_review_extractor import SystematicReviewExtractor
from systematic_review_extractor.models.schemas import ExtractionConfig

# Configure the extractor
config = ExtractionConfig(
    ai_provider="openai",
    model_name="gpt-4",
    confidence_threshold=0.8
)

# Initialize extractor
extractor = SystematicReviewExtractor(config)

# Extract from a single file
result = extractor.extract_from_file(
    Path("research_paper.pdf"),
    fields_to_extract=[
        "sample_size",
        "study_design", 
        "intervention",
        "primary_outcome",
        "p_value",
        "effect_size"
    ],
    extraction_context="This is a randomized controlled trial studying depression interventions"
)

# Print results
print(f"Study: {result.study_metadata.title}")
print(f"Validation passed: {result.validation_result.is_valid}")
for data in result.extracted_data:
    print(f"{data.field_name}: {data.value} (confidence: {data.confidence_score:.2f})")
```

### Batch Processing

```python
from pathlib import Path
from systematic_review_extractor.utils.exporters import ResultExporter

# Process multiple files
pdf_files = list(Path("papers/").glob("*.pdf"))
results = extractor.extract_from_files(
    pdf_files,
    ["sample_size", "intervention", "outcome"]
)

# Export results
exporter = ResultExporter()
exporter.export_to_excel(results, Path("systematic_review_results.xlsx"))

# Get processing statistics
stats = extractor.get_processing_stats(results)
print(f"Success rate: {stats.validation_pass_rate:.1%}")
print(f"Average processing time: {stats.average_processing_time:.2f}s")
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PROVIDER` | AI service provider (`openai` or `anthropic`) | `openai` |
| `MODEL_NAME` | AI model name | `gpt-4` |
| `OPENAI_API_KEY` | OpenAI API key | Required for OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required for Anthropic |
| `CONFIDENCE_THRESHOLD` | Minimum confidence for extracted data | `0.7` |
| `VALIDATION_ENABLED` | Enable validation checks | `true` |
| `RETRY_ATTEMPTS` | Number of retry attempts for failed extractions | `3` |
| `MAX_TOKENS` | Maximum tokens for AI responses | `4000` |
| `TEMPERATURE` | AI temperature setting | `0.1` |

### Field Types

The system can extract various types of data:

**Study Metadata**:
- `study_design` - Type of study (RCT, cohort, etc.)
- `sample_size` - Number of participants
- `population` - Study population description
- `intervention` - Treatment or intervention description
- `control` - Control group description

**Outcomes**:
- `primary_outcome` - Main study outcome
- `secondary_outcomes` - Additional outcomes
- `effect_size` - Effect size measures
- `p_value` - Statistical significance values
- `confidence_intervals` - 95% CI values

**Quality Metrics**:
- `randomization_method` - How randomization was performed
- `blinding` - Blinding procedures
- `dropout_rate` - Participant dropout percentage
- `follow_up_duration` - Length of follow-up

**Custom Fields**:
You can extract any custom field by specifying its name.

## Zero Hallucination Features

### Validation Framework

1. **Source Text Verification**: Ensures extracted data can be found in the original text
2. **Confidence Scoring**: Each extraction includes a confidence score
3. **Cross-referencing**: Validates extracted values against source material
4. **Field-specific Validation**: Type-appropriate checks (e.g., year ranges, p-value bounds)

### Quality Assurance

- **Retry Logic**: Automatic retries for low-confidence extractions
- **Multiple Validation Layers**: Semantic and syntactic validation
- **Error Reporting**: Detailed error messages and warnings
- **Audit Trail**: Complete logging of extraction process

## Output Formats

### JSON
```json
{
  "export_timestamp": "2024-01-15T10:30:00",
  "total_studies": 1,
  "results": [
    {
      "file_path": "study.pdf",
      "study_metadata": {
        "title": "Exercise for Depression: A Randomized Trial",
        "authors": [{"name": "John Smith"}],
        "publication_year": 2023
      },
      "extracted_data": [
        {
          "field_name": "sample_size",
          "value": "150 participants",
          "confidence_score": 0.95,
          "source_text": "A total of 150 participants were enrolled"
        }
      ],
      "validation_result": {
        "is_valid": true,
        "validation_score": 0.92
      }
    }
  ]
}
```

### CSV/Excel
Tabular format with columns for:
- Study metadata (title, authors, year, journal)
- Extracted field values and confidence scores
- Validation results
- Processing statistics

## Development

### Setup Development Environment

```bash
git clone https://github.com/matheus-rech/systematic-review-extractor.git
cd systematic-review-extractor
pip install -e .[dev]
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=systematic_review_extractor

# Run specific test file
pytest tests/test_extractor.py

# Run integration tests (requires API keys)
pytest -m integration
```

### Code Quality

```bash
# Format code
black systematic_review_extractor/

# Lint code
flake8 systematic_review_extractor/

# Type checking
mypy systematic_review_extractor/
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code is formatted
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{systematic_review_extractor,
  title={Systematic Review Extractor: AI-powered data extraction with zero hallucination guarantee},
  author={Rech, Matheus},
  year={2024},
  url={https://github.com/matheus-rech/systematic-review-extractor}
}
```

## Support

- **Issues**: [GitHub Issues](https://github.com/matheus-rech/systematic-review-extractor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/matheus-rech/systematic-review-extractor/discussions)
- **Documentation**: See the `/docs` directory for detailed documentation

## Changelog

### v0.1.0 (2024-01-15)
- Initial release
- Support for OpenAI and Anthropic AI providers
- PDF text extraction and processing
- Zero hallucination validation framework
- CLI interface and Python API
- Export to JSON, CSV, and Excel formats
- Comprehensive test suite
