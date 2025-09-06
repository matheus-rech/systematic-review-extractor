"""Data validation utilities."""

from typing import List, Dict, Any
from loguru import logger

from ..models.schemas import ExtractedData, ValidationResult, ExtractionConfig


class DataValidator:
    """Validate extracted data to prevent hallucinations and ensure quality."""
    
    def __init__(self, config: ExtractionConfig):
        """Initialize validator with configuration."""
        self.config = config
        self.confidence_threshold = config.confidence_threshold
    
    def validate_extraction_results(
        self, 
        extracted_data: List[ExtractedData], 
        original_text: str
    ) -> ValidationResult:
        """
        Validate a list of extracted data points.
        
        Args:
            extracted_data: List of extracted data to validate
            original_text: Original source text
            
        Returns:
            ValidationResult with overall validation status
        """
        errors = []
        warnings = []
        total_score = 0.0
        valid_extractions = 0
        
        for data in extracted_data:
            is_valid, score, field_errors, field_warnings = self._validate_single_extraction(
                data, original_text
            )
            
            if is_valid:
                valid_extractions += 1
                total_score += score
            
            errors.extend(field_errors)
            warnings.extend(field_warnings)
        
        # Calculate overall validation score
        if extracted_data:
            validation_score = total_score / len(extracted_data)
            is_valid = valid_extractions / len(extracted_data) >= 0.7  # 70% success rate
        else:
            validation_score = 0.0
            is_valid = False
            warnings.append("No data extracted")
        
        logger.info(
            f"Validation completed: {valid_extractions}/{len(extracted_data)} valid "
            f"(score: {validation_score:.2f})"
        )
        
        return ValidationResult(
            is_valid=is_valid,
            validation_score=validation_score,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_single_extraction(
        self, 
        data: ExtractedData, 
        original_text: str
    ) -> tuple[bool, float, List[str], List[str]]:
        """
        Validate a single extracted data point.
        
        Returns:
            Tuple of (is_valid, confidence_score, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check confidence threshold
        if data.confidence_score < self.confidence_threshold:
            warnings.append(
                f"Field '{data.field_name}' has low confidence: {data.confidence_score:.2f}"
            )
        
        # Validate source text exists in original
        if data.source_text and data.source_text.strip():
            if not self._text_exists_in_source(data.source_text, original_text):
                errors.append(
                    f"Source text for field '{data.field_name}' not found in original document"
                )
                return False, 0.1, errors, warnings
        else:
            warnings.append(f"No source text provided for field '{data.field_name}'")
        
        # Validate value is not empty or meaningless
        if not data.value or str(data.value).strip() in ['', 'None', 'null', 'N/A']:
            warnings.append(f"Empty or meaningless value for field '{data.field_name}'")
        
        # Field-specific validation
        field_errors, field_warnings = self._validate_field_specific(data)
        errors.extend(field_errors)
        warnings.extend(field_warnings)
        
        # Calculate validation score
        validation_score = data.confidence_score
        
        # Reduce score for warnings
        if warnings:
            validation_score *= 0.9
        
        is_valid = len(errors) == 0 and validation_score >= self.confidence_threshold
        
        return is_valid, validation_score, errors, warnings
    
    def _text_exists_in_source(self, extracted_text: str, original_text: str) -> bool:
        """Check if extracted text exists in original source."""
        # Normalize text for comparison
        extracted_normalized = ' '.join(extracted_text.strip().split()).lower()
        original_normalized = ' '.join(original_text.split()).lower()
        
        # Check exact match first
        if extracted_normalized in original_normalized:
            return True
        
        # Check fuzzy match for small differences
        if len(extracted_normalized) > 10:
            # Allow for small differences in longer text
            words = extracted_normalized.split()
            if len(words) >= 3:
                # Check if most words are present
                found_words = sum(1 for word in words if word in original_normalized)
                return found_words / len(words) >= 0.8
        
        return False
    
    def _validate_field_specific(self, data: ExtractedData) -> tuple[List[str], List[str]]:
        """Perform field-specific validation."""
        errors = []
        warnings = []
        
        field_name = data.field_name.lower()
        value = str(data.value)
        
        # Year validation
        if 'year' in field_name:
            try:
                year = int(value)
                if not (1900 <= year <= 2030):
                    errors.append(f"Invalid year value: {year}")
            except ValueError:
                errors.append(f"Year field contains non-numeric value: {value}")
        
        # DOI validation
        elif 'doi' in field_name:
            if value and not value.startswith(('10.', 'DOI:', 'doi:')):
                warnings.append(f"DOI format may be incorrect: {value}")
        
        # Sample size validation
        elif 'sample' in field_name or 'participants' in field_name or 'subjects' in field_name:
            try:
                if value.isdigit():
                    sample_size = int(value)
                    if sample_size < 1:
                        errors.append(f"Invalid sample size: {sample_size}")
                    elif sample_size > 1000000:
                        warnings.append(f"Very large sample size: {sample_size}")
            except ValueError:
                pass  # May contain additional text, which is okay
        
        # Percentage validation
        elif 'percent' in field_name or 'rate' in field_name:
            try:
                # Extract numeric part
                import re
                numeric_part = re.search(r'\d+\.?\d*', value)
                if numeric_part:
                    percent = float(numeric_part.group())
                    if not (0 <= percent <= 100):
                        warnings.append(f"Percentage value outside normal range: {percent}")
            except ValueError:
                pass
        
        # P-value validation
        elif 'p-value' in field_name or 'pvalue' in field_name:
            try:
                import re
                # Look for p-value pattern
                p_match = re.search(r'p\s*[=<>]\s*(\d+\.?\d*)', value.lower())
                if p_match:
                    p_val = float(p_match.group(1))
                    if not (0 <= p_val <= 1):
                        errors.append(f"Invalid p-value: {p_val}")
            except ValueError:
                pass
        
        return errors, warnings
    
    def validate_completeness(
        self, 
        extracted_data: List[ExtractedData], 
        required_fields: List[str]
    ) -> tuple[bool, List[str]]:
        """
        Validate that all required fields were extracted.
        
        Args:
            extracted_data: List of extracted data
            required_fields: List of field names that must be present
            
        Returns:
            Tuple of (is_complete, missing_fields)
        """
        extracted_fields = {data.field_name for data in extracted_data}
        missing_fields = [field for field in required_fields if field not in extracted_fields]
        
        is_complete = len(missing_fields) == 0
        
        if missing_fields:
            logger.warning(f"Missing required fields: {missing_fields}")
        
        return is_complete, missing_fields