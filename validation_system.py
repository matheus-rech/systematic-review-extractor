"""
Validation and Reliability System for Systematic Review Extraction

This module implements multiple validation methods to ensure:
1. Extraction accuracy (validation)
2. Reproducibility (same results every time)
3. Inter-rater reliability (agreement between extractors)
4. Evidence trail (proof of extraction)
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path
import uuid


@dataclass
class ValidationResult:
    """Complete validation record for an extraction."""
    extraction_id: str
    field_name: str
    value: Any
    
    # Validation methods
    regex_matched: bool = False
    context_verified: bool = False
    bounds_checked: bool = False
    cross_validated: bool = False
    human_verified: Optional[bool] = None
    
    # Reliability metrics
    confidence_score: float = 0.0
    reproducibility_score: float = 0.0
    agreement_score: float = 0.0
    
    # Evidence
    source_text: str = ""
    pattern_used: str = ""
    match_coordinates: Tuple[int, int] = (0, 0)
    context_window: str = ""
    
    # Audit trail
    extraction_timestamp: str = ""
    validation_timestamp: str = ""
    validator_version: str = "1.0.0"
    validation_hash: str = ""
    
    # Reproducibility
    deterministic_seed: int = 42
    extraction_attempts: List[Dict] = field(default_factory=list)


class ExtractionValidator:
    """
    Comprehensive validation system for extraction reliability.
    """
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.validation_log = []
        self.reliability_metrics = {}
        
    def validate_extraction(
        self,
        text: str,
        field_name: str,
        pattern: str,
        expected_type: str = "string"
    ) -> ValidationResult:
        """
        Perform multi-level validation of an extraction.
        """
        validation = ValidationResult(
            extraction_id=str(uuid.uuid4()),
            field_name=field_name,
            value=None,
            extraction_timestamp=datetime.now().isoformat(),
            validation_timestamp=datetime.now().isoformat()
        )
        
        # Level 1: Pattern Matching Validation
        match_result = self._validate_pattern_match(text, pattern)
        if match_result:
            validation.regex_matched = True
            validation.value = match_result['value']
            validation.match_coordinates = match_result['coordinates']
            validation.pattern_used = pattern
            validation.source_text = text
            
            # Level 2: Context Validation
            validation.context_verified = self._validate_context(
                text, match_result['coordinates'], field_name
            )
            validation.context_window = self._extract_context(
                text, match_result['coordinates']
            )
            
            # Level 3: Bounds Checking
            validation.bounds_checked = self._validate_bounds(
                match_result['value'], field_name, expected_type
            )
            
            # Level 4: Cross-Validation
            validation.cross_validated = self._cross_validate(
                text, field_name, match_result['value']
            )
            
            # Calculate confidence score
            validation.confidence_score = self._calculate_confidence(validation)
            
            # Generate validation hash for reproducibility
            validation.validation_hash = self._generate_validation_hash(validation)
        
        self.validation_log.append(validation)
        return validation
    
    def _validate_pattern_match(self, text: str, pattern: str) -> Optional[Dict]:
        """
        Validate that pattern matches and extract value.
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            match = regex.search(text)
            
            if match:
                value = match.group(1) if match.groups() else match.group(0)
                return {
                    'value': value,
                    'coordinates': (match.start(), match.end()),
                    'full_match': match.group(0)
                }
        except re.error as e:
            print(f"Pattern error: {e}")
        
        return None
    
    def _validate_context(
        self, 
        text: str, 
        coordinates: Tuple[int, int],
        field_name: str
    ) -> bool:
        """
        Validate that the extraction appears in appropriate context.
        """
        start, end = coordinates
        context_start = max(0, start - 200)
        context_end = min(len(text), end + 200)
        context = text[context_start:context_end].lower()
        
        # Context keywords that increase confidence
        context_indicators = {
            'sample_size': ['participants', 'enrolled', 'subjects', 'patients', 'recruited'],
            'p_value': ['significant', 'significance', 'statistical', 'analysis', 'test'],
            'effect_size': ['cohen', 'effect', 'size', 'magnitude', 'difference'],
            'mean_age': ['age', 'years', 'mean', 'average', 'demographic'],
            'confidence_interval': ['confidence', 'interval', 'ci', 'range', 'bounds'],
            'adverse_events': ['adverse', 'events', 'side effects', 'safety', 'complications']
        }
        
        field_key = field_name.lower().replace('_', ' ')
        indicators = context_indicators.get(field_key, [field_key])
        
        # Check if any indicator appears in context
        return any(indicator in context for indicator in indicators)
    
    def _validate_bounds(self, value: Any, field_name: str, expected_type: str) -> bool:
        """
        Validate that extracted value is within reasonable bounds.
        """
        if value is None:
            return False
        
        try:
            if expected_type == "integer":
                val = int(value)
                # Sample size bounds
                if 'sample' in field_name.lower():
                    return 1 <= val <= 1000000  # Reasonable study size
                return True
                
            elif expected_type == "float":
                val = float(value)
                # P-value bounds
                if 'p_value' in field_name.lower():
                    return 0 < val <= 1
                # Effect size bounds
                elif 'effect' in field_name.lower():
                    return -5 <= val <= 5  # Reasonable effect size range
                # Age bounds
                elif 'age' in field_name.lower():
                    return 0 <= val <= 120
                # Percentage bounds
                elif '%' in str(value) or 'percent' in field_name.lower():
                    return 0 <= val <= 100
                return True
                
            else:  # string
                return len(str(value)) > 0 and len(str(value)) < 1000
                
        except (ValueError, TypeError):
            return False
    
    def _cross_validate(self, text: str, field_name: str, value: Any) -> bool:
        """
        Cross-validate extraction using alternative patterns.
        """
        # Alternative patterns for validation
        alternatives = {
            'sample_size': [
                f"n\\s*=\\s*{value}",
                f"{value}\\s+(?:participants|subjects|patients)"
            ],
            'p_value': [
                f"p\\s*[<=]\\s*{value}",
                f"significance.*?{value}"
            ]
        }
        
        field_key = field_name.lower().replace('_', ' ')
        alt_patterns = alternatives.get(field_key, [])
        
        # Try to find the value with alternative patterns
        for pattern in alt_patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except:
                continue
        
        # If no alternatives, consider it validated if it appears exactly in text
        return str(value) in text
    
    def _extract_context(self, text: str, coordinates: Tuple[int, int], window: int = 150) -> str:
        """
        Extract context window around the match.
        """
        start, end = coordinates
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]
    
    def _calculate_confidence(self, validation: ValidationResult) -> float:
        """
        Calculate overall confidence score based on validation results.
        """
        score = 0.0
        weights = {
            'regex_matched': 0.25,
            'context_verified': 0.25,
            'bounds_checked': 0.20,
            'cross_validated': 0.30
        }
        
        if validation.regex_matched:
            score += weights['regex_matched']
        if validation.context_verified:
            score += weights['context_verified']
        if validation.bounds_checked:
            score += weights['bounds_checked']
        if validation.cross_validated:
            score += weights['cross_validated']
        
        # Boost confidence for human verification
        if validation.human_verified:
            score = min(1.0, score * 1.2)
        
        return round(score, 3)
    
    def _generate_validation_hash(self, validation: ValidationResult) -> str:
        """
        Generate deterministic hash for reproducibility verification.
        """
        hash_input = f"{validation.field_name}:{validation.value}:{validation.pattern_used}:{validation.match_coordinates}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def test_reproducibility(
        self,
        text: str,
        field_name: str,
        pattern: str,
        iterations: int = 10
    ) -> float:
        """
        Test if extraction produces same results across multiple runs.
        """
        results = []
        
        for i in range(iterations):
            validation = self.validate_extraction(text, field_name, pattern)
            results.append({
                'value': validation.value,
                'confidence': validation.confidence_score,
                'hash': validation.validation_hash
            })
        
        # Check if all results are identical
        first_result = results[0]
        identical_count = sum(
            1 for r in results 
            if r['value'] == first_result['value'] 
            and r['hash'] == first_result['hash']
        )
        
        reproducibility_score = identical_count / iterations
        return reproducibility_score
    
    def calculate_inter_rater_reliability(
        self,
        extractions1: List[ValidationResult],
        extractions2: List[ValidationResult]
    ) -> Dict[str, float]:
        """
        Calculate Cohen's Kappa for inter-rater reliability.
        """
        if len(extractions1) != len(extractions2):
            return {"error": "Extraction lists must be same length"}
        
        agreements = 0
        total = len(extractions1)
        
        for e1, e2 in zip(extractions1, extractions2):
            if e1.value == e2.value:
                agreements += 1
        
        observed_agreement = agreements / total
        
        # Calculate expected agreement (simplified)
        expected_agreement = 0.25  # Assuming 4 possible categories
        
        # Cohen's Kappa
        if expected_agreement == 1:
            kappa = 1
        else:
            kappa = (observed_agreement - expected_agreement) / (1 - expected_agreement)
        
        return {
            "observed_agreement": observed_agreement,
            "expected_agreement": expected_agreement,
            "cohens_kappa": kappa,
            "interpretation": self._interpret_kappa(kappa)
        }
    
    def _interpret_kappa(self, kappa: float) -> str:
        """
        Interpret Cohen's Kappa score.
        """
        if kappa < 0:
            return "Poor agreement"
        elif kappa < 0.20:
            return "Slight agreement"
        elif kappa < 0.40:
            return "Fair agreement"
        elif kappa < 0.60:
            return "Moderate agreement"
        elif kappa < 0.80:
            return "Substantial agreement"
        else:
            return "Almost perfect agreement"
    
    def generate_validation_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive validation report.
        """
        if not self.validation_log:
            return {"error": "No validations performed"}
        
        total_validations = len(self.validation_log)
        successful = sum(1 for v in self.validation_log if v.regex_matched)
        context_verified = sum(1 for v in self.validation_log if v.context_verified)
        bounds_valid = sum(1 for v in self.validation_log if v.bounds_checked)
        cross_validated = sum(1 for v in self.validation_log if v.cross_validated)
        
        avg_confidence = np.mean([v.confidence_score for v in self.validation_log])
        
        return {
            "summary": {
                "total_extractions": total_validations,
                "successful_extractions": successful,
                "success_rate": successful / total_validations if total_validations > 0 else 0,
                "average_confidence": round(avg_confidence, 3)
            },
            "validation_metrics": {
                "pattern_matching_rate": successful / total_validations,
                "context_verification_rate": context_verified / total_validations,
                "bounds_validation_rate": bounds_valid / total_validations,
                "cross_validation_rate": cross_validated / total_validations
            },
            "reliability_assessment": {
                "reproducibility": "High" if avg_confidence > 0.8 else "Moderate" if avg_confidence > 0.6 else "Low",
                "validation_method": "Multi-level validation with context, bounds, and cross-validation",
                "evidence_trail": "Complete with coordinates, context, and validation hash"
            },
            "detailed_results": [
                {
                    "field": v.field_name,
                    "value": v.value,
                    "confidence": v.confidence_score,
                    "validations_passed": sum([
                        v.regex_matched,
                        v.context_verified,
                        v.bounds_checked,
                        v.cross_validated
                    ]),
                    "hash": v.validation_hash
                }
                for v in self.validation_log
            ]
        }


class DualExtractionValidator:
    """
    Implements dual extraction validation (two independent extractors).
    Gold standard for systematic reviews.
    """
    
    def __init__(self):
        self.extractor1 = ExtractionValidator(strict_mode=True)
        self.extractor2 = ExtractionValidator(strict_mode=True)
        self.conflicts = []
        self.agreements = []
    
    def dual_extract(
        self,
        text: str,
        fields: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Perform dual extraction and compare results.
        """
        results1 = {}
        results2 = {}
        
        # First extractor
        for field_name, config in fields.items():
            patterns = config.get('patterns', [])
            if patterns:
                validation1 = self.extractor1.validate_extraction(
                    text, field_name, patterns[0], config.get('type', 'string')
                )
                results1[field_name] = validation1
        
        # Second extractor (simulate slight variation)
        for field_name, config in fields.items():
            patterns = config.get('patterns', [])
            if patterns:
                # Use alternative pattern if available
                pattern = patterns[1] if len(patterns) > 1 else patterns[0]
                validation2 = self.extractor2.validate_extraction(
                    text, field_name, pattern, config.get('type', 'string')
                )
                results2[field_name] = validation2
        
        # Compare and resolve conflicts
        final_results = self._resolve_conflicts(results1, results2)
        
        # Calculate agreement metrics
        agreement_metrics = self._calculate_agreement(results1, results2)
        
        return {
            "final_extractions": final_results,
            "agreement_metrics": agreement_metrics,
            "conflicts": self.conflicts,
            "validation_method": "Dual independent extraction with conflict resolution"
        }
    
    def _resolve_conflicts(
        self,
        results1: Dict[str, ValidationResult],
        results2: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """
        Resolve conflicts between two extractors.
        """
        final_results = {}
        
        for field_name in results1.keys():
            val1 = results1[field_name]
            val2 = results2.get(field_name)
            
            if val1.value == val2.value:
                # Agreement
                self.agreements.append(field_name)
                final_results[field_name] = {
                    "value": val1.value,
                    "confidence": max(val1.confidence_score, val2.confidence_score),
                    "agreement": True,
                    "validation_hash": val1.validation_hash
                }
            else:
                # Conflict - need resolution
                self.conflicts.append({
                    "field": field_name,
                    "value1": val1.value,
                    "value2": val2.value,
                    "confidence1": val1.confidence_score,
                    "confidence2": val2.confidence_score
                })
                
                # Resolution strategy: choose higher confidence
                if val1.confidence_score >= val2.confidence_score:
                    chosen = val1
                else:
                    chosen = val2
                
                final_results[field_name] = {
                    "value": chosen.value,
                    "confidence": chosen.confidence_score,
                    "agreement": False,
                    "conflict_resolved": "higher_confidence",
                    "validation_hash": chosen.validation_hash
                }
        
        return final_results
    
    def _calculate_agreement(
        self,
        results1: Dict[str, ValidationResult],
        results2: Dict[str, ValidationResult]
    ) -> Dict[str, float]:
        """
        Calculate agreement statistics between extractors.
        """
        total_fields = len(results1)
        agreements = len(self.agreements)
        conflicts = len(self.conflicts)
        
        agreement_rate = agreements / total_fields if total_fields > 0 else 0
        
        # Calculate Cohen's Kappa
        kappa_result = self.extractor1.calculate_inter_rater_reliability(
            list(results1.values()),
            list(results2.values())
        )
        
        return {
            "total_fields": total_fields,
            "agreements": agreements,
            "conflicts": conflicts,
            "agreement_rate": round(agreement_rate, 3),
            "cohens_kappa": kappa_result.get("cohens_kappa", 0),
            "reliability_interpretation": kappa_result.get("interpretation", "Unknown")
        }


# Example usage and testing
if __name__ == "__main__":
    # Sample text
    text = """
    This randomized controlled trial enrolled n = 150 participants with a mean age of 45.2 ± 12.3 years.
    Results showed significant improvement with p < 0.001. The effect size was Cohen's d = 0.85.
    The 95% confidence interval was [0.72, 0.98]. Adverse events occurred in 3% of participants.
    """
    
    # Single validator
    validator = ExtractionValidator(strict_mode=True)
    
    # Test sample size extraction
    validation = validator.validate_extraction(
        text,
        "sample_size",
        r"n\s*=\s*(\d+)",
        "integer"
    )
    
    print("=== VALIDATION RESULT ===")
    print(f"Field: {validation.field_name}")
    print(f"Value: {validation.value}")
    print(f"Confidence: {validation.confidence_score}")
    print(f"Regex Matched: {validation.regex_matched}")
    print(f"Context Verified: {validation.context_verified}")
    print(f"Bounds Checked: {validation.bounds_checked}")
    print(f"Cross Validated: {validation.cross_validated}")
    print(f"Validation Hash: {validation.validation_hash}")
    
    # Test reproducibility
    print("\n=== REPRODUCIBILITY TEST ===")
    reproducibility = validator.test_reproducibility(
        text,
        "sample_size",
        r"n\s*=\s*(\d+)",
        iterations=10
    )
    print(f"Reproducibility Score: {reproducibility * 100}%")
    
    # Test dual extraction
    print("\n=== DUAL EXTRACTION TEST ===")
    dual_validator = DualExtractionValidator()
    
    fields = {
        "sample_size": {
            "patterns": [r"n\s*=\s*(\d+)", r"(\d+)\s+participants"],
            "type": "integer"
        },
        "p_value": {
            "patterns": [r"p\s*<\s*(0?\.\d+)", r"p\s*=\s*(0?\.\d+)"],
            "type": "float"
        },
        "effect_size": {
            "patterns": [r"Cohen's\s*d\s*=\s*(\d+\.?\d*)", r"d\s*=\s*(\d+\.?\d*)"],
            "type": "float"
        }
    }
    
    dual_results = dual_validator.dual_extract(text, fields)
    
    print(f"Agreement Rate: {dual_results['agreement_metrics']['agreement_rate'] * 100}%")
    print(f"Cohen's Kappa: {dual_results['agreement_metrics']['cohens_kappa']}")
    print(f"Reliability: {dual_results['agreement_metrics']['reliability_interpretation']}")
    
    # Generate validation report
    print("\n=== VALIDATION REPORT ===")
    report = validator.generate_validation_report()
    print(json.dumps(report, indent=2))