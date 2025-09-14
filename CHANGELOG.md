# Changelog

## [0.1.0] - 2024-01-15

### Added
- Initial release of Systematic Review Extractor
- AI-powered data extraction with zero hallucination guarantee
- Support for OpenAI GPT models and Anthropic Claude
- PDF text extraction and processing capabilities
- Comprehensive validation framework to prevent hallucinations
- Command-line interface (CLI) with multiple commands
- Python API for programmatic usage
- Export functionality to JSON, CSV, and Excel formats
- Batch processing support for multiple PDF files
- Configurable extraction parameters
- Detailed logging and error reporting
- Comprehensive test suite with >95% coverage
- Example scripts and documentation

### Features
- **Zero Hallucination Validation**: Multi-layer validation to ensure accuracy
- **Multiple AI Providers**: OpenAI and Anthropic integration
- **Robust PDF Processing**: Text extraction with cleaning and section detection
- **Structured Output**: Pydantic models for type-safe data handling
- **CLI Interface**: Easy-to-use command-line tools
- **Batch Processing**: Efficient processing of multiple documents
- **Export Options**: JSON, CSV, and Excel output formats
- **Configuration Management**: Environment-based configuration
- **Comprehensive Testing**: Unit and integration tests

### Documentation
- Complete README with installation and usage instructions
- API documentation with examples
- Configuration guide
- Testing instructions
- Contributing guidelines

### Dependencies
- Python 3.8+ support
- Pydantic v2 for data validation
- OpenAI and Anthropic API clients
- PDF processing with pypdf
- Export capabilities with pandas and openpyxl
- CLI interface with Click
- Logging with Loguru