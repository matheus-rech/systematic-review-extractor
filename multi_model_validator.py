#!/usr/bin/env python3
"""
Multi-Model Validation System for Systematic Review Extraction
Uses multiple independent models to confirm extraction accuracy
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import aiohttp
from pathlib import Path
import anthropic
import openai
from abc import ABC, abstractmethod


@dataclass
class ModelValidation:
    """Validation result from a single model."""
    model_name: str
    extracted_value: Any
    confidence: float
    reasoning: str
    timestamp: str
    agreement: bool = False


@dataclass
class ConsensusResult:
    """Consensus result from multiple models."""
    field: str
    consensus_value: Any
    confidence: float
    model_agreements: List[ModelValidation]
    consensus_method: str
    final_decision: str


class BaseExtractorModel(ABC):
    """Base class for extraction models."""
    
    @abstractmethod
    async def extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Extract data from text."""
        pass
    
    @abstractmethod
    def validate_extraction(self, value: Any, context: str) -> float:
        """Validate an extraction."""
        pass


class ClaudeExtractor(BaseExtractorModel):
    """Claude-based extraction model."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
        else:
            self.client = None
        self.model_name = "Claude-3"
    
    async def extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Extract using Claude."""
        if not self.client:
            # Fallback to pattern matching if no API key
            return self._pattern_extract(text, field, pattern)
        
        try:
            prompt = f"""Extract the {field} from this text. 
            Expected pattern: {pattern}
            Text: {text[:1000]}
            
            Return only the extracted value and your confidence (0-1)."""
            
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response (simplified)
            content = response.content[0].text
            value = content.split('\n')[0] if content else None
            confidence = 0.85  # Default high confidence for Claude
            
            return ModelValidation(
                model_name=self.model_name,
                extracted_value=value,
                confidence=confidence,
                reasoning="Claude extraction",
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            return self._pattern_extract(text, field, pattern)
    
    def _pattern_extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Fallback pattern-based extraction."""
        import re
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            value = matches[0] if isinstance(matches[0], str) else matches[0][0]
            return ModelValidation(
                model_name=f"{self.model_name}-pattern",
                extracted_value=value,
                confidence=0.75,
                reasoning="Pattern matching",
                timestamp=datetime.now().isoformat()
            )
        return ModelValidation(
            model_name=self.model_name,
            extracted_value=None,
            confidence=0.0,
            reasoning="No match found",
            timestamp=datetime.now().isoformat()
        )
    
    def validate_extraction(self, value: Any, context: str) -> float:
        """Validate extraction using context."""
        if value and str(value) in context:
            return 0.9
        return 0.5


class GPTExtractor(BaseExtractorModel):
    """GPT-based extraction model."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            openai.api_key = self.api_key
            self.client = openai
        else:
            self.client = None
        self.model_name = "GPT-4"
    
    async def extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Extract using GPT."""
        if not self.client:
            return self._pattern_extract(text, field, pattern)
        
        try:
            response = self.client.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract data from research papers."},
                    {"role": "user", "content": f"Extract {field} from: {text[:1000]}"}
                ],
                max_tokens=100
            )
            
            content = response.choices[0].message.content
            value = content.strip() if content else None
            
            return ModelValidation(
                model_name=self.model_name,
                extracted_value=value,
                confidence=0.82,
                reasoning="GPT extraction",
                timestamp=datetime.now().isoformat()
            )
        except Exception:
            return self._pattern_extract(text, field, pattern)
    
    def _pattern_extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Fallback pattern extraction."""
        import re
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            value = matches[0] if isinstance(matches[0], str) else matches[0][0]
            return ModelValidation(
                model_name=f"{self.model_name}-pattern",
                extracted_value=value,
                confidence=0.73,
                reasoning="Pattern matching",
                timestamp=datetime.now().isoformat()
            )
        return ModelValidation(
            model_name=self.model_name,
            extracted_value=None,
            confidence=0.0,
            reasoning="No match found",
            timestamp=datetime.now().isoformat()
        )
    
    def validate_extraction(self, value: Any, context: str) -> float:
        """Validate extraction."""
        if value and str(value) in context:
            return 0.88
        return 0.45


class LocalLLMExtractor(BaseExtractorModel):
    """Local LLM extraction (Ollama, LlamaCpp, etc.)."""
    
    def __init__(self, model_name: str = "llama2"):
        self.model_name = f"Local-{model_name}"
        self.base_url = "http://localhost:11434"  # Ollama default
    
    async def extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Extract using local LLM."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": "llama2",
                        "prompt": f"Extract {field} from: {text[:500]}",
                        "stream": False
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        value = data.get("response", "").strip()
                        return ModelValidation(
                            model_name=self.model_name,
                            extracted_value=value,
                            confidence=0.78,
                            reasoning="Local LLM extraction",
                            timestamp=datetime.now().isoformat()
                        )
        except Exception:
            pass
        
        # Fallback to pattern matching
        return self._pattern_extract(text, field, pattern)
    
    def _pattern_extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Pattern-based extraction."""
        import re
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            value = matches[0] if isinstance(matches[0], str) else matches[0][0]
            return ModelValidation(
                model_name=f"{self.model_name}-pattern",
                extracted_value=value,
                confidence=0.70,
                reasoning="Pattern matching",
                timestamp=datetime.now().isoformat()
            )
        return ModelValidation(
            model_name=self.model_name,
            extracted_value=None,
            confidence=0.0,
            reasoning="No match found",
            timestamp=datetime.now().isoformat()
        )
    
    def validate_extraction(self, value: Any, context: str) -> float:
        """Validate extraction."""
        if value and str(value) in context:
            return 0.85
        return 0.4


class RegexExtractor(BaseExtractorModel):
    """Pure regex-based extraction for baseline."""
    
    def __init__(self):
        self.model_name = "Regex-Baseline"
    
    async def extract(self, text: str, field: str, pattern: str) -> ModelValidation:
        """Extract using regex."""
        import re
        try:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                confidence = self._calculate_confidence(value, text)
                
                return ModelValidation(
                    model_name=self.model_name,
                    extracted_value=value,
                    confidence=confidence,
                    reasoning=f"Regex pattern: {pattern[:30]}...",
                    timestamp=datetime.now().isoformat()
                )
        except Exception as e:
            pass
        
        return ModelValidation(
            model_name=self.model_name,
            extracted_value=None,
            confidence=0.0,
            reasoning="No regex match",
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_confidence(self, value: str, text: str) -> float:
        """Calculate confidence based on value characteristics."""
        confidence = 0.6  # Base confidence
        
        # Numeric values are more reliable
        if value and value.replace('.', '').isdigit():
            confidence += 0.2
        
        # Check if value appears multiple times (less likely to be error)
        if text.count(str(value)) > 1:
            confidence += 0.1
        
        return min(confidence, 0.95)
    
    def validate_extraction(self, value: Any, context: str) -> float:
        """Validate extraction."""
        if value and str(value) in context:
            return 0.8
        return 0.3


class MultiModelValidator:
    """
    Orchestrates multiple models for validation and consensus.
    """
    
    def __init__(self, use_llms: bool = True):
        """
        Initialize with available models.
        
        Args:
            use_llms: Whether to use LLM APIs (requires API keys)
        """
        self.models = [RegexExtractor()]  # Always include regex
        
        if use_llms:
            # Add LLM models if API keys available
            if os.getenv("ANTHROPIC_API_KEY"):
                self.models.append(ClaudeExtractor())
            
            if os.getenv("OPENAI_API_KEY"):
                self.models.append(GPTExtractor())
            
            # Try local LLM
            self.models.append(LocalLLMExtractor())
        
        self.consensus_threshold = 0.7  # 70% agreement needed
    
    async def validate_extraction(
        self,
        text: str,
        field: str,
        pattern: str,
        initial_value: Any = None
    ) -> ConsensusResult:
        """
        Validate extraction using multiple models.
        
        Args:
            text: Source text
            field: Field being extracted
            pattern: Regex pattern
            initial_value: Initial extraction to validate
        
        Returns:
            ConsensusResult with final decision
        """
        # Get extractions from all models
        tasks = [
            model.extract(text, field, pattern) 
            for model in self.models
        ]
        
        validations = await asyncio.gather(*tasks)
        
        # Calculate consensus
        consensus = self._calculate_consensus(validations, initial_value)
        
        return consensus
    
    def _calculate_consensus(
        self,
        validations: List[ModelValidation],
        initial_value: Any = None
    ) -> ConsensusResult:
        """
        Calculate consensus from multiple model validations.
        """
        # Count value occurrences
        value_counts = {}
        total_confidence = 0
        
        for validation in validations:
            if validation.extracted_value:
                value = str(validation.extracted_value)
                if value not in value_counts:
                    value_counts[value] = {
                        'count': 0,
                        'confidence': 0,
                        'models': []
                    }
                
                value_counts[value]['count'] += 1
                value_counts[value]['confidence'] += validation.confidence
                value_counts[value]['models'].append(validation)
                total_confidence += validation.confidence
        
        # Include initial value if provided
        if initial_value:
            value = str(initial_value)
            if value not in value_counts:
                value_counts[value] = {
                    'count': 1,
                    'confidence': 0.7,
                    'models': [ModelValidation(
                        model_name="Initial-Extraction",
                        extracted_value=initial_value,
                        confidence=0.7,
                        reasoning="Original extraction",
                        timestamp=datetime.now().isoformat()
                    )]
                }
        
        # Find consensus value
        if not value_counts:
            return ConsensusResult(
                field="",
                consensus_value=None,
                confidence=0.0,
                model_agreements=[],
                consensus_method="No values found",
                final_decision="No consensus"
            )
        
        # Sort by count and confidence
        sorted_values = sorted(
            value_counts.items(),
            key=lambda x: (x[1]['count'], x[1]['confidence']),
            reverse=True
        )
        
        consensus_value = sorted_values[0][0]
        consensus_data = sorted_values[0][1]
        
        # Calculate agreement percentage
        total_models = len(self.models) + (1 if initial_value else 0)
        agreement_rate = consensus_data['count'] / total_models
        
        # Calculate final confidence
        avg_confidence = consensus_data['confidence'] / consensus_data['count']
        final_confidence = avg_confidence * agreement_rate
        
        # Mark agreements
        for validation in consensus_data['models']:
            validation.agreement = True
        
        # Determine final decision
        if agreement_rate >= self.consensus_threshold:
            final_decision = f"High confidence: {agreement_rate:.0%} agreement"
        elif agreement_rate >= 0.5:
            final_decision = f"Moderate confidence: {agreement_rate:.0%} agreement"
        else:
            final_decision = f"Low confidence: {agreement_rate:.0%} agreement"
        
        return ConsensusResult(
            field="",
            consensus_value=consensus_value,
            confidence=final_confidence,
            model_agreements=validations,
            consensus_method=f"Majority vote ({consensus_data['count']}/{total_models})",
            final_decision=final_decision
        )
    
    async def validate_all_extractions(
        self,
        extractions: List[Dict[str, Any]],
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Validate all extractions using multiple models.
        
        Args:
            extractions: List of extraction dictionaries
            text: Source text
        
        Returns:
            Enhanced extractions with validation results
        """
        validated_extractions = []
        
        for extraction in extractions:
            field = extraction.get('field', '')
            pattern = extraction.get('pattern', '')
            value = extraction.get('value')
            
            # Get consensus
            consensus = await self.validate_extraction(
                text=text,
                field=field,
                pattern=pattern,
                initial_value=value
            )
            
            # Enhance extraction with validation
            extraction['multi_model_validation'] = {
                'consensus_value': consensus.consensus_value,
                'consensus_confidence': consensus.confidence,
                'models_agreed': len([m for m in consensus.model_agreements if m.agreement]),
                'total_models': len(consensus.model_agreements),
                'consensus_method': consensus.consensus_method,
                'final_decision': consensus.final_decision,
                'model_details': [
                    {
                        'model': m.model_name,
                        'value': m.extracted_value,
                        'confidence': m.confidence,
                        'agreed': m.agreement
                    }
                    for m in consensus.model_agreements
                ]
            }
            
            # Update confidence if consensus is higher
            if consensus.confidence > extraction.get('confidence', 0):
                extraction['confidence'] = consensus.confidence
                extraction['confidence_source'] = 'multi-model consensus'
            
            validated_extractions.append(extraction)
        
        return validated_extractions


# Example usage
async def validate_extraction_example():
    """Example of using multi-model validation."""
    
    # Initialize validator
    validator = MultiModelValidator(use_llms=True)
    
    # Sample text
    text = """
    This randomized controlled trial enrolled n = 250 patients.
    The mortality rate was 15.3% in the intervention group.
    Statistical significance was achieved with p < 0.001.
    """
    
    # Validate sample size extraction
    result = await validator.validate_extraction(
        text=text,
        field="sample_size",
        pattern=r"n\s*=\s*(\d+)",
        initial_value="250"
    )
    
    print(f"Consensus value: {result.consensus_value}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Decision: {result.final_decision}")
    print(f"Models agreed: {len([m for m in result.model_agreements if m.agreement])}/{len(result.model_agreements)}")


if __name__ == "__main__":
    # Run example
    asyncio.run(validate_extraction_example())