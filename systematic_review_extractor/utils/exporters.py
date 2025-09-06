"""Export utilities for systematic review extraction results."""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from loguru import logger

from ..models.schemas import ExtractionResult, ProcessingStats


class ResultExporter:
    """Export extraction results to various formats."""
    
    def __init__(self):
        """Initialize result exporter."""
        pass
    
    def export_to_json(
        self, 
        results: List[ExtractionResult], 
        output_path: Path,
        include_metadata: bool = True
    ) -> None:
        """
        Export results to JSON format.
        
        Args:
            results: List of extraction results
            output_path: Path to output JSON file
            include_metadata: Whether to include processing metadata
        """
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_studies": len(results),
            "results": []
        }
        
        for result in results:
            result_dict = {
                "file_path": result.file_path,
                "study_metadata": result.study_metadata.dict(),
                "extracted_data": [data.dict() for data in result.extracted_data],
                "validation_result": result.validation_result.dict()
            }
            
            if include_metadata:
                result_dict.update({
                    "extraction_timestamp": result.extraction_timestamp.isoformat(),
                    "processing_time_seconds": result.processing_time_seconds
                })
            
            export_data["results"].append(result_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(results)} results to JSON: {output_path}")
    
    def export_to_csv(
        self, 
        results: List[ExtractionResult], 
        output_path: Path,
        flatten_data: bool = True
    ) -> None:
        """
        Export results to CSV format.
        
        Args:
            results: List of extraction results
            output_path: Path to output CSV file
            flatten_data: Whether to flatten extracted data into columns
        """
        if not results:
            logger.warning("No results to export")
            return
        
        # Prepare data for CSV
        csv_data = []
        
        for result in results:
            base_row = {
                "file_path": result.file_path,
                "title": result.study_metadata.title,
                "authors": "; ".join([author.name for author in result.study_metadata.authors]),
                "publication_year": result.study_metadata.publication_year,
                "journal": result.study_metadata.journal,
                "doi": result.study_metadata.doi,
                "study_type": result.study_metadata.study_type,
                "validation_passed": result.validation_result.is_valid,
                "validation_score": result.validation_result.validation_score,
                "processing_time": result.processing_time_seconds
            }
            
            if flatten_data:
                # Create one row with all extracted data as columns
                for data in result.extracted_data:
                    base_row[f"{data.field_name}_value"] = data.value
                    base_row[f"{data.field_name}_confidence"] = data.confidence_score
                    base_row[f"{data.field_name}_source"] = data.source_text[:100] + "..." if len(data.source_text) > 100 else data.source_text
                
                csv_data.append(base_row)
            else:
                # Create one row per extracted data point
                if result.extracted_data:
                    for data in result.extracted_data:
                        row = base_row.copy()
                        row.update({
                            "field_name": data.field_name,
                            "extracted_value": data.value,
                            "confidence_score": data.confidence_score,
                            "source_text": data.source_text,
                            "extraction_method": data.extraction_method
                        })
                        csv_data.append(row)
                else:
                    csv_data.append(base_row)
        
        # Write to CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"Exported {len(csv_data)} rows to CSV: {output_path}")
        else:
            logger.warning("No data to export to CSV")
    
    def export_to_excel(
        self, 
        results: List[ExtractionResult], 
        output_path: Path,
        create_summary_sheet: bool = True
    ) -> None:
        """
        Export results to Excel format with multiple sheets.
        
        Args:
            results: List of extraction results
            output_path: Path to output Excel file
            create_summary_sheet: Whether to create a summary sheet
        """
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Main data sheet
            self._create_main_data_sheet(results, writer)
            
            # Study metadata sheet
            self._create_metadata_sheet(results, writer)
            
            # Validation results sheet
            self._create_validation_sheet(results, writer)
            
            # Summary sheet
            if create_summary_sheet:
                self._create_summary_sheet(results, writer)
        
        logger.info(f"Exported results to Excel: {output_path}")
    
    def _create_main_data_sheet(self, results: List[ExtractionResult], writer):
        """Create main data sheet with extracted values."""
        data_rows = []
        
        for result in results:
            for data in result.extracted_data:
                data_rows.append({
                    "Study Title": result.study_metadata.title,
                    "File Path": result.file_path,
                    "Field Name": data.field_name,
                    "Extracted Value": data.value,
                    "Confidence Score": data.confidence_score,
                    "Source Text": data.source_text,
                    "Extraction Method": data.extraction_method,
                    "Page Number": data.page_number
                })
        
        if data_rows:
            df = pd.DataFrame(data_rows)
            df.to_excel(writer, sheet_name="Extracted Data", index=False)
    
    def _create_metadata_sheet(self, results: List[ExtractionResult], writer):
        """Create study metadata sheet."""
        metadata_rows = []
        
        for result in results:
            metadata = result.study_metadata
            metadata_rows.append({
                "File Path": result.file_path,
                "Title": metadata.title,
                "Authors": "; ".join([author.name for author in metadata.authors]),
                "Publication Year": metadata.publication_year,
                "Journal": metadata.journal,
                "DOI": metadata.doi,
                "Study Type": metadata.study_type,
                "Keywords": "; ".join(metadata.keywords),
                "Abstract": metadata.abstract[:500] + "..." if len(metadata.abstract or "") > 500 else metadata.abstract
            })
        
        if metadata_rows:
            df = pd.DataFrame(metadata_rows)
            df.to_excel(writer, sheet_name="Study Metadata", index=False)
    
    def _create_validation_sheet(self, results: List[ExtractionResult], writer):
        """Create validation results sheet."""
        validation_rows = []
        
        for result in results:
            validation = result.validation_result
            validation_rows.append({
                "File Path": result.file_path,
                "Study Title": result.study_metadata.title,
                "Is Valid": validation.is_valid,
                "Validation Score": validation.validation_score,
                "Errors": "; ".join(validation.errors),
                "Warnings": "; ".join(validation.warnings),
                "Processing Time (s)": result.processing_time_seconds
            })
        
        if validation_rows:
            df = pd.DataFrame(validation_rows)
            df.to_excel(writer, sheet_name="Validation Results", index=False)
    
    def _create_summary_sheet(self, results: List[ExtractionResult], writer):
        """Create summary statistics sheet."""
        if not results:
            return
        
        # Calculate summary statistics
        total_studies = len(results)
        successful_extractions = len([r for r in results if r.extracted_data])
        avg_processing_time = sum(r.processing_time_seconds for r in results) / total_studies
        validation_pass_rate = len([r for r in results if r.validation_result.is_valid]) / total_studies
        
        # Field extraction statistics
        field_stats = {}
        for result in results:
            for data in result.extracted_data:
                field_name = data.field_name
                if field_name not in field_stats:
                    field_stats[field_name] = {"count": 0, "avg_confidence": 0, "total_confidence": 0}
                
                field_stats[field_name]["count"] += 1
                field_stats[field_name]["total_confidence"] += data.confidence_score
        
        # Calculate average confidence per field
        for field_name in field_stats:
            stats = field_stats[field_name]
            stats["avg_confidence"] = stats["total_confidence"] / stats["count"]
        
        # Create summary data
        summary_data = [
            ["Metric", "Value"],
            ["Total Studies", total_studies],
            ["Successful Extractions", successful_extractions],
            ["Success Rate", f"{successful_extractions/total_studies*100:.1f}%"],
            ["Validation Pass Rate", f"{validation_pass_rate*100:.1f}%"],
            ["Average Processing Time (s)", f"{avg_processing_time:.2f}"],
            ["", ""],
            ["Field Extraction Statistics", ""],
            ["Field Name", "Extraction Count", "Average Confidence"]
        ]
        
        for field_name, stats in sorted(field_stats.items()):
            summary_data.append([
                field_name, 
                stats["count"], 
                f"{stats['avg_confidence']:.3f}"
            ])
        
        # Convert to DataFrame and save
        df = pd.DataFrame(summary_data)
        df.to_excel(writer, sheet_name="Summary", index=False, header=False)
    
    def export_processing_stats(self, stats: ProcessingStats, output_path: Path) -> None:
        """
        Export processing statistics to JSON.
        
        Args:
            stats: Processing statistics
            output_path: Path to output JSON file
        """
        stats_dict = stats.dict()
        stats_dict["export_timestamp"] = datetime.now().isoformat()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats_dict, f, indent=2)
        
        logger.info(f"Exported processing statistics to: {output_path}")