"""AI-powered data extraction using language models."""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not available")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic package not available")

from ..models.schemas import ExtractedData, ExtractionConfig


class AIExtractor:
    """AI-powered data extraction with hallucination prevention."""
    
    def __init__(self, config: ExtractionConfig):
        """Initialize AI extractor with configuration."""
        self.config = config
        self.client = None
        
        if config.ai_provider == "openai" and OPENAI_AVAILABLE:
            self.client = openai.OpenAI()
        elif config.ai_provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic()
        else:
            raise ValueError(f"AI provider '{config.ai_provider}' not available or not installed")
    
    def extract_structured_data(
        self, 
        text: str, 
        fields_to_extract: List[str],
        context: Optional[str] = None
    ) -> List[ExtractedData]:
        """
        Extract structured data from text using AI.
        
        Args:
            text: Source text to extract from
            fields_to_extract: List of field names to extract
            context: Optional context to provide to the AI
            
        Returns:
            List of extracted data points
        """
        start_time = time.time()
        
        # Create extraction prompt
        prompt = self._create_extraction_prompt(text, fields_to_extract, context)
        
        # Extract data with retries
        extracted_data = []
        for field in fields_to_extract:
            for attempt in range(self.config.retry_attempts):
                try:
                    result = self._extract_single_field(text, field, prompt)
                    if result:
                        extracted_data.append(result)
                        break
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed for field '{field}': {e}")
                    if attempt == self.config.retry_attempts - 1:
                        logger.error(f"Failed to extract field '{field}' after {self.config.retry_attempts} attempts")
        
        processing_time = time.time() - start_time
        logger.info(f"Extracted {len(extracted_data)} fields in {processing_time:.2f} seconds")
        
        return extracted_data
    
    def _create_extraction_prompt(
        self, 
        text: str, 
        fields_to_extract: List[str], 
        context: Optional[str] = None
    ) -> str:
        """Create a prompt for data extraction."""
        
        base_prompt = """You are a systematic review data extraction assistant. Your task is to extract specific information from research papers with ZERO HALLUCINATION.

CRITICAL RULES:
1. ONLY extract information that is EXPLICITLY stated in the text
2. If information is not present, respond with "NOT_FOUND"
3. Always provide the exact source text where you found the information
4. Do not infer, assume, or generate any information
5. Be precise and conservative in your extractions

"""
        
        if context:
            base_prompt += f"Context: {context}\n\n"
        
        base_prompt += f"""Fields to extract: {', '.join(fields_to_extract)}

Text to analyze:
{text[:4000]}  # Truncate to avoid token limits

For each field, respond in this JSON format:
{{
    "field_name": "exact_field_name",
    "value": "extracted_value_or_NOT_FOUND",
    "source_text": "exact_text_where_found_or_empty_if_not_found",
    "confidence": 0.0-1.0
}}

Extract one field at a time and be extremely careful to avoid hallucination."""
        
        return base_prompt
    
    def _extract_single_field(self, text: str, field: str, base_prompt: str) -> Optional[ExtractedData]:
        """Extract a single field using AI."""
        
        field_prompt = f"{base_prompt}\n\nExtract ONLY the field: '{field}'"
        
        try:
            if self.config.ai_provider == "openai":
                response = self._call_openai(field_prompt)
            elif self.config.ai_provider == "anthropic":
                response = self._call_anthropic(field_prompt)
            else:
                raise ValueError(f"Unsupported AI provider: {self.config.ai_provider}")
            
            # Parse response
            extracted_info = self._parse_ai_response(response, field)
            
            if extracted_info and extracted_info['value'] != "NOT_FOUND":
                return ExtractedData(
                    field_name=field,
                    value=extracted_info['value'],
                    confidence_score=extracted_info.get('confidence', 0.5),
                    source_text=extracted_info.get('source_text', ''),
                    extraction_method=f"ai_{self.config.ai_provider}"
                )
            
        except Exception as e:
            logger.error(f"Failed to extract field '{field}': {e}")
        
        return None
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=[
                {"role": "system", "content": "You are a precise data extraction assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        return response.choices[0].message.content
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _parse_ai_response(self, response: str, field: str) -> Optional[Dict[str, Any]]:
        """Parse AI response and extract structured data."""
        try:
            # Try to parse as JSON first
            if '{' in response and '}' in response:
                # Extract JSON part
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
                data = json.loads(json_str)
                
                # Validate required fields
                if 'field_name' in data and 'value' in data:
                    return data
            
            # Fallback: try to extract information from text
            lines = response.strip().split('\n')
            extracted_info = {
                'field_name': field,
                'value': 'NOT_FOUND',
                'source_text': '',
                'confidence': 0.1
            }
            
            for line in lines:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'value' in key:
                        extracted_info['value'] = value
                    elif 'source' in key:
                        extracted_info['source_text'] = value
                    elif 'confidence' in key:
                        try:
                            extracted_info['confidence'] = float(value)
                        except ValueError:
                            pass
            
            return extracted_info
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None
    
    def validate_extraction(self, extracted_data: ExtractedData, original_text: str) -> Tuple[bool, float]:
        """
        Validate extracted data against original text to prevent hallucination.
        
        Args:
            extracted_data: The extracted data to validate
            original_text: Original source text
            
        Returns:
            Tuple of (is_valid, confidence_score)
        """
        try:
            # Check if source text exists in original text
            if extracted_data.source_text and extracted_data.source_text.strip():
                # Normalize text for comparison
                normalized_source = ' '.join(extracted_data.source_text.split())
                normalized_original = ' '.join(original_text.split())
                
                # Check if source text is found in original
                if normalized_source.lower() in normalized_original.lower():
                    # Additional validation: check if extracted value makes sense in context
                    value_str = str(extracted_data.value).lower()
                    source_str = extracted_data.source_text.lower()
                    
                    # If value is found in source text, higher confidence
                    if value_str in source_str:
                        return True, min(0.95, extracted_data.confidence_score + 0.2)
                    else:
                        return True, extracted_data.confidence_score
                else:
                    logger.warning(f"Source text not found in original for field '{extracted_data.field_name}'")
                    return False, 0.1
            else:
                # No source text provided - lower confidence
                return True, max(0.3, extracted_data.confidence_score - 0.2)
                
        except Exception as e:
            logger.error(f"Validation failed for field '{extracted_data.field_name}': {e}")
            return False, 0.1