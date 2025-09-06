#!/usr/bin/env python3
"""
Process the Dewan 2018 PDF with comprehensive extraction patterns
"""

import json
from pathlib import Path
from working_pdf_extractor import WorkingPDFExtractor

def process_dewan_2018():
    """Process the Dewan 2018 paper with medical/surgical extraction patterns."""
    
    # Path to the PDF
    pdf_path = "/Users/matheusrech/Documents/dewan2018.pdf"
    
    # Define comprehensive extraction patterns for medical papers
    patterns = {
        # Sample sizes
        "total_patients": [
            r"n\s*=\s*(\d+)\s*patients?",
            r"(\d+)\s*patients?\s*were\s*(?:included|enrolled|studied)",
            r"total\s*of\s*(\d+)\s*patients?",
            r"(\d+)\s*consecutive\s*patients?",
            r"cohort\s*of\s*(\d+)",
            r"sample\s*size.*?(\d+)",
            r"enrolled\s*(\d+)\s*patients?"
        ],
        
        # Age data
        "age": [
            r"age.*?(\d+\.?\d*)\s*±\s*(\d+\.?\d*)",
            r"mean\s*age.*?(\d+\.?\d*)",
            r"median\s*age.*?(\d+\.?\d*)",
            r"age\s*range.*?(\d+)\s*[-–]\s*(\d+)",
            r"(\d+\.?\d*)\s*years?\s*old",
            r"aged\s*(\d+\.?\d*)\s*±\s*(\d+\.?\d*)"
        ],
        
        # Gender distribution
        "male_female": [
            r"(\d+)\s*males?\s*and\s*(\d+)\s*females?",
            r"(\d+)\s*men\s*and\s*(\d+)\s*women",
            r"male.*?(\d+).*?female.*?(\d+)",
            r"(\d+\.?\d*)%?\s*male",
            r"(\d+\.?\d*)%?\s*female",
            r"M:F.*?(\d+):(\d+)"
        ],
        
        # Surgical/procedure data
        "procedure": [
            r"decompressive\s*craniectomy",
            r"craniectomy",
            r"surgical\s*decompression",
            r"hemicraniectomy",
            r"bifrontal\s*decompression",
            r"frontotemporal.*?craniectomy"
        ],
        
        # Outcomes - mortality
        "mortality": [
            r"mortality.*?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%?\s*mortality",
            r"died.*?(\d+).*?patients?",
            r"(\d+)\s*deaths?",
            r"death.*?(\d+\.?\d*)%",
            r"survival.*?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%?\s*survived"
        ],
        
        # Outcomes - functional
        "gos_outcome": [
            r"GOS.*?(\d+)",
            r"Glasgow\s*Outcome\s*Scale.*?(\d+)",
            r"good\s*outcome.*?(\d+\.?\d*)%",
            r"favorable\s*outcome.*?(\d+\.?\d*)%",
            r"poor\s*outcome.*?(\d+\.?\d*)%",
            r"unfavorable\s*outcome.*?(\d+\.?\d*)%"
        ],
        
        # Clinical scores
        "gcs_score": [
            r"GCS.*?(\d+)",
            r"Glasgow\s*Coma\s*Scale.*?(\d+)",
            r"GCS\s*score.*?(\d+)",
            r"admission\s*GCS.*?(\d+)",
            r"initial\s*GCS.*?(\d+)"
        ],
        
        # ICP values
        "icp_values": [
            r"ICP.*?(\d+\.?\d*)\s*mm\s*Hg",
            r"intracranial\s*pressure.*?(\d+\.?\d*)",
            r"(\d+\.?\d*)\s*mm\s*Hg",
            r"ICP\s*>\s*(\d+)",
            r"ICP\s*threshold.*?(\d+)"
        ],
        
        # Timing data
        "time_to_surgery": [
            r"(\d+\.?\d*)\s*hours?\s*(?:after|from|since)",
            r"within\s*(\d+\.?\d*)\s*hours?",
            r"time\s*to\s*surgery.*?(\d+\.?\d*)",
            r"operated.*?(\d+\.?\d*)\s*hours?"
        ],
        
        # Complications
        "complications": [
            r"complications?.*?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%?\s*complications?",
            r"infection.*?(\d+\.?\d*)%",
            r"hydrocephalus.*?(\d+\.?\d*)%",
            r"hemorrhage.*?(\d+\.?\d*)%",
            r"seizure.*?(\d+\.?\d*)%"
        ],
        
        # Statistical values
        "p_values": [
            r"p\s*[<=>]\s*([\d.]+)",
            r"P\s*[<=>]\s*([\d.]+)",
            r"p-value.*?([\d.]+)",
            r"significant.*?p\s*[<=>]\s*([\d.]+)"
        ],
        
        # Confidence intervals
        "confidence_intervals": [
            r"95%\s*CI.*?([\d.]+)\s*[-–]\s*([\d.]+)",
            r"CI.*?\[([\d.]+)[,\s]+([\d.]+)\]",
            r"\(([\d.]+)\s*[-–]\s*([\d.]+)\)",
            r"confidence\s*interval.*?([\d.]+)\s*to\s*([\d.]+)"
        ],
        
        # Follow-up period
        "follow_up": [
            r"follow[- ]up.*?(\d+)\s*months?",
            r"(\d+)\s*months?\s*follow[- ]up",
            r"followed.*?(\d+)\s*months?",
            r"(\d+)\s*year\s*follow[- ]up"
        ],
        
        # Study period
        "study_period": [
            r"between\s*(\d{4})\s*and\s*(\d{4})",
            r"from\s*(\w+\s*\d{4})\s*to\s*(\w+\s*\d{4})",
            r"(\d{4})\s*[-–]\s*(\d{4})",
            r"conducted.*?(\d{4})"
        ],
        
        # Inclusion/Exclusion
        "inclusion_criteria": [
            r"inclusion\s*criteria",
            r"included\s*if",
            r"eligible\s*if",
            r"were\s*included"
        ],
        
        # Volume measurements
        "volume_measurements": [
            r"(\d+\.?\d*)\s*ml",
            r"(\d+\.?\d*)\s*cc",
            r"(\d+\.?\d*)\s*cm³",
            r"volume.*?(\d+\.?\d*)",
            r"hematoma.*?(\d+\.?\d*)\s*ml"
        ]
    }
    
    # Initialize extractor
    extractor = WorkingPDFExtractor(output_dir="dewan2018_extraction")
    
    print("=" * 70)
    print("PROCESSING DEWAN 2018 PDF")
    print("=" * 70)
    print(f"\nPDF: {pdf_path}")
    print("\nExtracting medical/surgical data with evidence trail...")
    print("-" * 50)
    
    try:
        # Process the PDF
        results = extractor.extract_from_pdf(pdf_path, patterns)
        
        # Display summary
        print(f"\n✅ EXTRACTION COMPLETE")
        print(f"Total extractions: {results['summary']['total_extractions']}")
        print(f"Fields found: {len(results['summary']['fields_found'])} unique fields")
        print(f"Pages analyzed: {results['pdf_info']['pages']} pages")
        
        # Group extractions by field
        by_field = {}
        for ext in results["extractions"]:
            field = ext["field"]
            if field not in by_field:
                by_field[field] = []
            by_field[field].append(ext)
        
        # Display key findings
        print("\n📊 KEY FINDINGS WITH EVIDENCE:")
        print("=" * 70)
        
        for field_name in sorted(by_field.keys()):
            extractions = by_field[field_name]
            print(f"\n📌 {field_name.upper().replace('_', ' ')}:")
            print("-" * 50)
            
            # Show unique values for this field
            unique_values = {}
            for ext in extractions[:5]:  # Limit to first 5
                if ext["value"] not in unique_values:
                    unique_values[ext["value"]] = ext
                    print(f"  Value: {ext['value']}")
                    print(f"  Page: {ext['page']}, Coordinates: [{', '.join(f'{c:.1f}' for c in ext['coordinates'][:4])}]")
                    print(f"  Match: \"{ext['exact_match'][:60]}...\"" if len(ext['exact_match']) > 60 else f"  Match: \"{ext['exact_match']}\"")
                    print(f"  Screenshot: {ext['screenshot']}")
                    print(f"  Confidence: {ext['confidence']:.0%}")
                    print(f"  Verification: {ext['verification_hash']}")
                    print()
            
            if len(extractions) > 5:
                print(f"  ... and {len(extractions) - 5} more extractions")
        
        # Save complete results
        output_file = Path("dewan2018_extraction") / "json" / "dewan2018_results.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            # Remove base64 from saved file
            save_results = results.copy()
            for ext in save_results["extractions"]:
                ext.pop("screenshot_base64", None)
                ext["context"] = ext["context"][:100] + "..." if len(ext.get("context", "")) > 100 else ext.get("context", "")
            json.dump(save_results, f, indent=2, default=str)
        
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"✅ Successfully processed: {pdf_path}")
        print(f"✅ Total extractions: {results['summary']['total_extractions']}")
        print(f"✅ Screenshots created: {results['summary']['total_extractions']}")
        print(f"✅ Evidence preserved: Every extraction has coordinates + screenshot")
        print(f"✅ Results saved to: {output_file}")
        print(f"✅ Screenshots in: dewan2018_extraction/screenshots/")
        
        # Create a summary report
        summary = {
            "pdf": "dewan2018.pdf",
            "total_pages": results['pdf_info']['pages'],
            "total_extractions": results['summary']['total_extractions'],
            "unique_fields": len(results['summary']['fields_found']),
            "key_findings": {}
        }
        
        # Extract key medical data if found
        for field in ["total_patients", "mortality", "age", "procedure", "gcs_score", "follow_up"]:
            if field in by_field:
                values = list(set([ext["value"] for ext in by_field[field]]))
                summary["key_findings"][field] = values[:3]  # Top 3 unique values
        
        print("\n📋 MEDICAL DATA SUMMARY:")
        print("-" * 50)
        for field, values in summary["key_findings"].items():
            print(f"{field}: {', '.join(str(v) for v in values)}")
        
        return True
        
    except FileNotFoundError:
        print(f"\n❌ Error: PDF file not found at {pdf_path}")
        print("Please check the file path and try again.")
        return False
    except Exception as e:
        print(f"\n❌ Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Process the Dewan 2018 PDF
    success = process_dewan_2018()
    
    if success:
        print("\n" + "🎉 " * 20)
        print("SUCCESS! Processed your PDF with complete evidence trail!")
        print("🎉 " * 20)
        print("\nCheck the 'dewan2018_extraction' folder for:")
        print("• screenshots/ - Visual evidence with highlights")
        print("• json/ - Complete extraction data")
    else:
        print("\n⚠️ Processing failed. Please check the error message above.")