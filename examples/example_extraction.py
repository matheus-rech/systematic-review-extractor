#!/usr/bin/env python3
"""
Example script demonstrating the Systematic Review Extractor.

This script shows how to use the extractor to process research papers
and extract structured data with validation.
"""

import os
from pathlib import Path
from systematic_review_extractor import SystematicReviewExtractor
from systematic_review_extractor.models.schemas import ExtractionConfig
from systematic_review_extractor.utils.config import ConfigManager, setup_logging
from systematic_review_extractor.utils.exporters import ResultExporter


def main():
    """Run the example extraction."""
    
    # Setup logging
    setup_logging("INFO")
    
    print("Systematic Review Extractor - Example")
    print("=" * 50)
    
    # Check if API keys are available
    config_manager = ConfigManager()
    api_status = config_manager.validate_api_keys()
    
    if not any(api_status.values()):
        print("⚠️  No API keys found!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your environment")
        print("Or create a .env file with your keys")
        print("\nExample .env file:")
        print(config_manager.get_sample_config())
        return
    
    # Create configuration
    available_provider = "openai" if api_status["openai"] else "anthropic"
    model_name = "gpt-4" if available_provider == "openai" else "claude-3-sonnet-20240229"
    
    config = ExtractionConfig(
        ai_provider=available_provider,
        model_name=model_name,
        confidence_threshold=0.7,
        validation_enabled=True
    )
    
    print(f"✓ Using {available_provider.upper()} with model {model_name}")
    
    # Initialize extractor
    try:
        extractor = SystematicReviewExtractor(config)
        print("✓ Extractor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize extractor: {e}")
        return
    
    # Define fields to extract
    fields_to_extract = [
        "study_design",
        "sample_size",
        "population", 
        "intervention",
        "primary_outcome",
        "effect_size",
        "p_value",
        "conclusion"
    ]
    
    print(f"✓ Will extract {len(fields_to_extract)} fields: {', '.join(fields_to_extract)}")
    
    # Look for sample PDF files
    sample_dir = Path("examples/sample_papers")
    if not sample_dir.exists():
        sample_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("\n📁 No sample PDF files found!")
        print(f"Please add some research paper PDFs to: {sample_dir}")
        print("The extractor will process any .pdf files in that directory")
        
        # Create a sample text file instead for demonstration
        sample_text_file = sample_dir / "sample_study_text.txt"
        with open(sample_text_file, 'w') as f:
            f.write("""
Sample Research Paper Text
==========================

Title: Effectiveness of Exercise Interventions on Depression: A Randomized Controlled Trial

Authors: Dr. Sarah Johnson, Dr. Michael Chen, Dr. Emma Wilson

Abstract:
Background: Depression affects millions of people worldwide. This study investigated the effectiveness of structured exercise interventions.

Methods: This was a randomized controlled trial with 240 participants aged 18-65 with major depressive disorder. Participants were randomized to either a 12-week supervised exercise program (n=120) or a control group receiving standard care (n=120).

Results: The exercise group showed significant improvement in Beck Depression Inventory scores compared to control (mean difference: -8.5 points, 95% CI: -12.1 to -4.9, p < 0.001). Effect size was large (Cohen's d = 0.85).

Conclusion: Structured exercise interventions are highly effective for reducing depression symptoms in adults.
            """.strip())
        
        print(f"💡 Created sample text file: {sample_text_file}")
        print("For full functionality, add actual PDF files to the directory")
        return
    
    print(f"📄 Found {len(pdf_files)} PDF files to process")
    
    # Process files
    try:
        print("\n🔄 Starting extraction...")
        
        if len(pdf_files) == 1:
            # Single file processing
            result = extractor.extract_from_file(
                pdf_files[0], 
                fields_to_extract,
                "Extract data from this systematic review or research paper"
            )
            results = [result]
        else:
            # Batch processing
            results = extractor.extract_from_files(
                pdf_files,
                fields_to_extract,
                "Extract data from systematic reviews and research papers"
            )
        
        print(f"✓ Extraction completed! Processed {len(results)} files")
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return
    
    # Display results summary
    print("\n📊 RESULTS SUMMARY")
    print("-" * 30)
    
    for i, result in enumerate(results, 1):
        print(f"\nFile {i}: {Path(result.file_path).name}")
        print(f"  Title: {result.study_metadata.title}")
        print(f"  Validation: {'✓ Passed' if result.validation_result.is_valid else '❌ Failed'}")
        print(f"  Score: {result.validation_result.validation_score:.2f}")
        print(f"  Extracted fields: {len(result.extracted_data)}")
        print(f"  Processing time: {result.processing_time_seconds:.2f}s")
        
        # Show some extracted data
        if result.extracted_data:
            print("  Sample extractions:")
            for data in result.extracted_data[:3]:  # Show first 3
                value_preview = str(data.value)[:50] + "..." if len(str(data.value)) > 50 else str(data.value)
                print(f"    • {data.field_name}: {value_preview} (conf: {data.confidence_score:.2f})")
    
    # Export results
    output_dir = Path("examples/output")
    output_dir.mkdir(exist_ok=True)
    
    exporter = ResultExporter()
    
    # Export to different formats
    json_file = output_dir / f"extraction_results_{len(results)}files.json"
    csv_file = output_dir / f"extraction_results_{len(results)}files.csv"
    excel_file = output_dir / f"extraction_results_{len(results)}files.xlsx"
    
    try:
        exporter.export_to_json(results, json_file)
        exporter.export_to_csv(results, csv_file)
        exporter.export_to_excel(results, excel_file)
        
        print(f"\n💾 Results exported to:")
        print(f"  JSON: {json_file}")
        print(f"  CSV: {csv_file}")
        print(f"  Excel: {excel_file}")
        
    except Exception as e:
        print(f"⚠️  Export failed: {e}")
    
    # Processing statistics
    stats = extractor.get_processing_stats(results)
    print(f"\n📈 PROCESSING STATISTICS")
    print("-" * 30)
    print(f"Total files: {stats.total_files}")
    print(f"Successful extractions: {stats.successful_extractions}")
    print(f"Success rate: {stats.successful_extractions/stats.total_files*100:.1f}%")
    print(f"Validation pass rate: {stats.validation_pass_rate:.1%}")
    print(f"Average processing time: {stats.average_processing_time:.2f}s")
    print(f"Total processing time: {stats.total_processing_time:.2f}s")
    
    print("\n🎉 Example completed successfully!")
    print("\nNext steps:")
    print("- Add your own PDF files to examples/sample_papers/")
    print("- Customize the fields_to_extract list for your needs")
    print("- Use the CLI: sr-extract extract your_papers/ --fields your_field")


if __name__ == "__main__":
    main()