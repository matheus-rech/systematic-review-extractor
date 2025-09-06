"""Main systematic review extractor class."""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger

from ..models.schemas import (
    ExtractionResult,
    ExtractionConfig,
    StudyMetadata,
    ValidationResult,
    Author,
    ProcessingStats
)
from ..extractors.pdf_extractor import PDFExtractor, TextProcessor
from ..extractors.ai_extractor import AIExtractor
from ..utils.validators import DataValidator
from ..utils.config import ConfigManager


class SystematicReviewExtractor:
    """Main class for systematic review data extraction."""
    
    def __init__(self, config: Optional[ExtractionConfig] = None):
        """
        Initialize the systematic review extractor.
        
        Args:
            config: Extraction configuration. If None, uses default config.
        """
        self.config = config or ExtractionConfig()
        self.pdf_extractor = PDFExtractor()
        self.text_processor = TextProcessor()
        self.ai_extractor = AIExtractor(self.config)
        self.validator = DataValidator(self.config) if self.config.validation_enabled else None
        
        logger.info(f"Initialized SystematicReviewExtractor with {self.config.ai_provider} provider")
    
    def extract_from_file(
        self, 
        file_path: Path, 
        fields_to_extract: List[str],
        extraction_context: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract structured data from a single PDF file.
        
        Args:
            file_path: Path to the PDF file
            fields_to_extract: List of field names to extract
            extraction_context: Optional context for extraction
            
        Returns:
            ExtractionResult containing all extracted data and metadata
            
        Raises:
            ValueError: If file cannot be processed
        """
        start_time = time.time()
        logger.info(f"Starting extraction from {file_path}")
        
        try:
            # Extract text from PDF
            full_text, page_texts = self.pdf_extractor.extract_text(file_path)
            pdf_metadata = self.pdf_extractor.extract_metadata(file_path)
            
            # Clean and process text
            cleaned_text = self.text_processor.clean_text(full_text)
            sections = self.text_processor.split_into_sections(cleaned_text)
            
            # Extract study metadata
            study_metadata = self._extract_study_metadata(cleaned_text, sections, pdf_metadata)
            
            # Extract specified data fields
            extracted_data = self.ai_extractor.extract_structured_data(
                cleaned_text, 
                fields_to_extract, 
                extraction_context
            )
            
            # Validate extracted data
            validation_result = self._validate_extraction(extracted_data, cleaned_text)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            result = ExtractionResult(
                study_metadata=study_metadata,
                extracted_data=extracted_data,
                validation_result=validation_result,
                processing_time_seconds=processing_time,
                file_path=str(file_path)
            )
            
            logger.info(
                f"Extraction completed: {len(extracted_data)} fields extracted "
                f"in {processing_time:.2f}s (validation: {validation_result.is_valid})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract from {file_path}: {e}")
            raise ValueError(f"Extraction failed: {e}")
    
    def extract_from_files(
        self, 
        file_paths: List[Path], 
        fields_to_extract: List[str],
        extraction_context: Optional[str] = None
    ) -> List[ExtractionResult]:
        """
        Extract structured data from multiple PDF files.
        
        Args:
            file_paths: List of paths to PDF files
            fields_to_extract: List of field names to extract
            extraction_context: Optional context for extraction
            
        Returns:
            List of ExtractionResult objects
        """
        results = []
        total_start_time = time.time()
        
        logger.info(f"Starting batch extraction from {len(file_paths)} files")
        
        for i, file_path in enumerate(file_paths, 1):
            try:
                logger.info(f"Processing file {i}/{len(file_paths)}: {file_path.name}")
                result = self.extract_from_file(file_path, fields_to_extract, extraction_context)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                # Continue with other files
                continue
        
        total_time = time.time() - total_start_time
        logger.info(f"Batch extraction completed: {len(results)}/{len(file_paths)} files processed in {total_time:.2f}s")
        
        return results
    
    def _extract_study_metadata(
        self, 
        text: str, 
        sections: Dict[str, str], 
        pdf_metadata: Dict[str, Any]
    ) -> StudyMetadata:
        """Extract study metadata from text and PDF metadata."""
        
        # Try to extract title
        title = pdf_metadata.get('title', '')
        if not title or len(title.strip()) < 5:
            # Try to extract from text
            title = self._extract_title_from_text(text, sections)
        
        # Extract authors
        authors = self._extract_authors(text, sections, pdf_metadata)
        
        # Extract other metadata using AI
        metadata_fields = ['publication_year', 'journal', 'doi', 'study_type']
        metadata_extractions = self.ai_extractor.extract_structured_data(
            text[:2000],  # Use first part for metadata
            metadata_fields,
            "Extract bibliographic metadata from this research paper"
        )
        
        # Convert extractions to metadata dict
        metadata_dict = {}
        for extraction in metadata_extractions:
            if extraction.confidence_score >= self.config.confidence_threshold:
                metadata_dict[extraction.field_name] = extraction.value
        
        # Extract abstract
        abstract = sections.get('abstract', '').strip()
        if not abstract:
            abstract = self._extract_abstract_from_text(text)
        
        return StudyMetadata(
            title=title.strip(),
            authors=authors,
            publication_year=self._safe_int_convert(metadata_dict.get('publication_year')),
            journal=metadata_dict.get('journal', '').strip(),
            doi=metadata_dict.get('doi', '').strip(),
            abstract=abstract,
            study_type=metadata_dict.get('study_type', '').strip()
        )
    
    def _extract_title_from_text(self, text: str, sections: Dict[str, str]) -> str:
        """Extract title from text."""
        lines = text.split('\n')[:10]  # Look in first 10 lines
        
        for line in lines:
            line = line.strip()
            # Title is usually one of the first substantial lines
            if len(line) > 10 and len(line) < 200 and not line.lower().startswith(('abstract', 'introduction')):
                return line
        
        return "Title not found"
    
    def _extract_authors(self, text: str, sections: Dict[str, str], pdf_metadata: Dict[str, Any]) -> List[Author]:
        """Extract authors from text and metadata."""
        authors = []
        
        # Try PDF metadata first
        pdf_author = pdf_metadata.get('author', '').strip()
        if pdf_author:
            # Simple parsing - could be enhanced
            author_names = [name.strip() for name in pdf_author.split(',')]
            for name in author_names:
                if name:
                    authors.append(Author(name=name))
        
        # If no authors found, try AI extraction
        if not authors:
            author_extractions = self.ai_extractor.extract_structured_data(
                text[:1000],
                ['authors'],
                "Extract author names from this research paper"
            )
            
            for extraction in author_extractions:
                if extraction.field_name == 'authors' and extraction.confidence_score >= 0.5:
                    # Parse author string
                    author_text = str(extraction.value)
                    names = [name.strip() for name in author_text.split(',')]
                    for name in names:
                        if name and len(name) > 2:
                            authors.append(Author(name=name))
        
        return authors
    
    def _extract_abstract_from_text(self, text: str) -> str:
        """Extract abstract from text using simple heuristics."""
        lines = text.split('\n')
        
        abstract_start = -1
        for i, line in enumerate(lines):
            if 'abstract' in line.lower():
                abstract_start = i
                break
        
        if abstract_start >= 0:
            # Extract next few lines as abstract
            abstract_lines = []
            for i in range(abstract_start + 1, min(abstract_start + 20, len(lines))):
                line = lines[i].strip()
                if line and not line.lower().startswith(('introduction', 'keywords', '1.')):
                    abstract_lines.append(line)
                elif line.lower().startswith(('introduction', 'keywords')):
                    break
            
            return ' '.join(abstract_lines)
        
        return ""
    
    def _safe_int_convert(self, value: Any) -> Optional[int]:
        """Safely convert value to integer."""
        if value is None:
            return None
        
        try:
            if isinstance(value, str):
                # Extract year from string (e.g., "2023" from "Published in 2023")
                import re
                year_match = re.search(r'\b(19|20)\d{2}\b', value)
                if year_match:
                    return int(year_match.group())
            
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def _validate_extraction(self, extracted_data: List, original_text: str) -> ValidationResult:
        """Validate extracted data."""
        if not self.validator:
            return ValidationResult(
                is_valid=True,
                validation_score=1.0,
                errors=[],
                warnings=["Validation disabled"]
            )
        
        return self.validator.validate_extraction_results(extracted_data, original_text)
    
    def get_processing_stats(self, results: List[ExtractionResult]) -> ProcessingStats:
        """Calculate processing statistics from extraction results."""
        if not results:
            return ProcessingStats(
                total_files=0,
                successful_extractions=0,
                failed_extractions=0,
                average_processing_time=0.0,
                total_processing_time=0.0,
                validation_pass_rate=0.0
            )
        
        total_files = len(results)
        successful_extractions = len([r for r in results if r.extracted_data])
        failed_extractions = total_files - successful_extractions
        total_processing_time = sum(r.processing_time_seconds for r in results)
        average_processing_time = total_processing_time / total_files if total_files > 0 else 0
        validation_passes = len([r for r in results if r.validation_result.is_valid])
        validation_pass_rate = validation_passes / total_files if total_files > 0 else 0
        
        return ProcessingStats(
            total_files=total_files,
            successful_extractions=successful_extractions,
            failed_extractions=failed_extractions,
            average_processing_time=average_processing_time,
            total_processing_time=total_processing_time,
            validation_pass_rate=validation_pass_rate
        )