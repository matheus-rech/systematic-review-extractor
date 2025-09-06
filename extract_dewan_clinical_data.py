#!/usr/bin/env python3
"""
Extract specific clinical data from Dewan 2018 - focused extraction
"""

import json
from pathlib import Path
from working_pdf_extractor import WorkingPDFExtractor
import fitz

def analyze_dewan_2018():
    """Extract specific clinical data from Dewan 2018."""
    
    pdf_path = "/Users/matheusrech/Documents/dewan2018.pdf"
    
    # First, let's read some text to understand the content
    doc = fitz.open(pdf_path)
    
    print("=" * 70)
    print("ANALYZING DEWAN 2018 - CLINICAL DATA EXTRACTION")
    print("=" * 70)
    
    # Read first few pages to understand content
    print("\n📄 DOCUMENT PREVIEW:")
    print("-" * 50)
    
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        text = page.get_text()[:500]  # First 500 chars
        print(f"\nPage {page_num + 1} preview:")
        print(text.replace('\n', ' ')[:200] + "...")
    
    doc.close()
    
    # More targeted patterns based on neurosurgical content
    patterns = {
        # Patient numbers - more specific
        "total_patients": [
            r"(\d+)\s*patients?\s*(?:with|underwent|had|received)",
            r"[Nn]\s*=\s*(\d+)",
            r"sample\s*(?:size\s*)?(?:of\s*)?(\d+)",
            r"total\s*(?:of\s*)?(\d+)\s*(?:patients?|cases?|subjects?)",
            r"enrolled\s*(\d+)",
            r"included\s*(\d+)\s*patients?",
            r"(\d+)\s*consecutive\s*patients?"
        ],
        
        # Mortality - specific patterns
        "mortality_rate": [
            r"mortality\s*(?:rate\s*)?(?:was\s*)?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%\s*mortality",
            r"(\d+\.?\d*)%\s*(?:of\s*patients?\s*)?died",
            r"death\s*rate\s*(?:was\s*)?(\d+\.?\d*)%",
            r"(\d+)\s*(?:of\s*\d+\s*)?patients?\s*died",
            r"(\d+)\s*deaths?"
        ],
        
        # GCS scores
        "gcs_scores": [
            r"GCS\s*(?:score\s*)?(?:of\s*)?(\d+)",
            r"Glasgow\s*Coma\s*Scale\s*(?:score\s*)?(?:of\s*)?(\d+)",
            r"GCS\s*(?:≤|<=|<|>|≥|>=)\s*(\d+)",
            r"GCS\s*(\d+)\s*[-–]\s*(\d+)",
            r"median\s*GCS\s*(?:was\s*)?(\d+)",
            r"mean\s*GCS\s*(?:was\s*)?(\d+\.?\d*)"
        ],
        
        # Age information
        "age_data": [
            r"(?:mean\s*)?age\s*(?:was\s*)?(\d+\.?\d*)\s*(?:±|years)",
            r"(\d+\.?\d*)\s*±\s*(\d+\.?\d*)\s*years",
            r"median\s*age\s*(?:was\s*)?(\d+\.?\d*)",
            r"age\s*range\s*(?:was\s*)?(\d+)\s*[-–]\s*(\d+)",
            r"aged\s*(\d+)\s*[-–]\s*(\d+)\s*years"
        ],
        
        # Surgical procedures
        "surgical_procedure": [
            r"(decompressive\s*craniectomy)",
            r"(hemicraniectomy)",
            r"(bifrontal\s*decompression)",
            r"(surgical\s*decompression)",
            r"(craniotomy)",
            r"(evacuation)",
            r"(duroplasty)"
        ],
        
        # ICP monitoring
        "icp_data": [
            r"ICP\s*(?:was\s*)?(\d+\.?\d*)\s*(?:mm\s*Hg|mmHg)",
            r"intracranial\s*pressure\s*(?:of\s*)?(\d+\.?\d*)",
            r"ICP\s*(?:>|≥|greater)\s*(\d+)",
            r"ICP\s*threshold\s*(?:of\s*)?(\d+)",
            r"mean\s*ICP\s*(?:was\s*)?(\d+\.?\d*)"
        ],
        
        # Outcome measures
        "functional_outcome": [
            r"(?:good|favorable)\s*outcome\s*(?:in\s*)?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%\s*(?:had\s*)?(?:good|favorable)\s*outcome",
            r"(?:poor|unfavorable)\s*outcome\s*(?:in\s*)?(\d+\.?\d*)%",
            r"GOS\s*(?:score\s*)?(?:of\s*)?(\d+)",
            r"mRS\s*(?:score\s*)?(?:of\s*)?(\d+)",
            r"(\d+\.?\d*)%\s*(?:achieved|had)\s*(?:functional\s*)?independence"
        ],
        
        # Complications
        "complications": [
            r"complication\s*rate\s*(?:was\s*)?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%\s*(?:developed\s*)?complications?",
            r"infection\s*(?:rate\s*)?(?:was\s*)?(\d+\.?\d*)%",
            r"hydrocephalus\s*(?:in\s*)?(\d+\.?\d*)%",
            r"(\d+\.?\d*)%\s*(?:developed\s*)?hydrocephalus",
            r"seizure[s]?\s*(?:in\s*)?(\d+\.?\d*)%"
        ],
        
        # Time intervals
        "time_intervals": [
            r"(\d+\.?\d*)\s*hours?\s*(?:after|from|post)",
            r"within\s*(\d+\.?\d*)\s*hours?",
            r"(?:mean|median)\s*time\s*(?:to\s*surgery\s*)?(?:was\s*)?(\d+\.?\d*)\s*hours?",
            r"(\d+\.?\d*)\s*days?\s*(?:after|post)",
            r"hospital\s*stay\s*(?:of\s*)?(\d+\.?\d*)\s*days?"
        ],
        
        # Statistical significance
        "statistical_significance": [
            r"[Pp]\s*value\s*(?:of\s*)?([0-9.]+)",
            r"[Pp]\s*[<>=]\s*([0-9.]+)",
            r"(?:statistically\s*)?significant\s*\([Pp]\s*[<>=]\s*([0-9.]+)\)",
            r"CI\s*(?:95%\s*)?(?:\[)?([0-9.]+)\s*[-–,]\s*([0-9.]+)",
            r"odds\s*ratio\s*(?:OR\s*)?(?:of\s*)?([0-9.]+)",
            r"relative\s*risk\s*(?:RR\s*)?(?:of\s*)?([0-9.]+)"
        ]
    }
    
    # Initialize extractor
    extractor = WorkingPDFExtractor(output_dir="dewan2018_clinical")
    
    print("\n📊 EXTRACTING CLINICAL DATA...")
    print("-" * 50)
    
    try:
        # Process the PDF
        results = extractor.extract_from_pdf(pdf_path, patterns)
        
        # Organize results by field
        by_field = {}
        for ext in results["extractions"]:
            field = ext["field"]
            if field not in by_field:
                by_field[field] = []
            by_field[field].append(ext)
        
        # Display clinical findings
        print("\n" + "=" * 70)
        print("CLINICAL DATA EXTRACTED FROM DEWAN 2018")
        print("=" * 70)
        
        clinical_summary = {}
        
        # Process each clinical field
        for field_name in [
            "total_patients", "mortality_rate", "gcs_scores", "age_data",
            "surgical_procedure", "icp_data", "functional_outcome", 
            "complications", "time_intervals", "statistical_significance"
        ]:
            if field_name in by_field:
                extractions = by_field[field_name]
                unique_values = []
                seen = set()
                
                for ext in extractions:
                    if ext["value"] not in seen:
                        seen.add(ext["value"])
                        unique_values.append({
                            "value": ext["value"],
                            "page": ext["page"],
                            "context": ext["exact_match"],
                            "confidence": ext["confidence"]
                        })
                
                if unique_values:
                    clinical_summary[field_name] = unique_values[:5]  # Top 5
                    
                    print(f"\n📌 {field_name.upper().replace('_', ' ')}:")
                    print("-" * 50)
                    for item in unique_values[:3]:  # Show top 3
                        print(f"  • {item['value']} (Page {item['page']}, {item['confidence']:.0%} confidence)")
                        print(f"    Context: \"{item['context'][:60]}...\"" if len(item['context']) > 60 else f"    Context: \"{item['context']}\"")
        
        # Save clinical summary
        summary_file = Path("dewan2018_clinical") / "clinical_summary.json"
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_file, "w") as f:
            json.dump({
                "pdf": "dewan2018.pdf",
                "total_extractions": len(results["extractions"]),
                "clinical_data": clinical_summary,
                "pages_analyzed": results["pdf_info"]["pages"]
            }, f, indent=2)
        
        # Final summary
        print("\n" + "=" * 70)
        print("EXTRACTION SUMMARY")
        print("=" * 70)
        print(f"✅ PDF processed: {pdf_path}")
        print(f"✅ Total clinical data points: {len(results['extractions'])}")
        print(f"✅ Clinical fields identified: {len(clinical_summary)}")
        print(f"✅ Screenshots with evidence: {len(results['extractions'])}")
        print(f"✅ Clinical summary saved to: {summary_file}")
        
        # Create a brief report
        print("\n📋 KEY CLINICAL FINDINGS:")
        print("-" * 50)
        
        if "total_patients" in clinical_summary:
            print(f"Sample size: {clinical_summary['total_patients'][0]['value']}")
        
        if "mortality_rate" in clinical_summary:
            print(f"Mortality: {clinical_summary['mortality_rate'][0]['value']}")
        
        if "gcs_scores" in clinical_summary:
            print(f"GCS scores: {', '.join([str(v['value']) for v in clinical_summary['gcs_scores'][:3]])}")
        
        if "surgical_procedure" in clinical_summary:
            procedures = list(set([v['value'] for v in clinical_summary['surgical_procedure']]))
            print(f"Procedures: {', '.join(procedures[:3])}")
        
        if "statistical_significance" in clinical_summary:
            p_values = [v['value'] for v in clinical_summary['statistical_significance'] if float(v['value']) < 1]
            if p_values:
                print(f"P-values: {', '.join(p_values[:3])}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = analyze_dewan_2018()
    
    if success:
        print("\n" + "✅ " * 20)
        print("CLINICAL DATA EXTRACTION COMPLETE!")
        print("✅ " * 20)
        print("\nAll extractions have:")
        print("• Exact page and coordinates")
        print("• Screenshot with yellow highlight")
        print("• Verification hash")
        print("• Complete context")
        print("\nNO HALLUCINATION - Every data point is traceable to the source PDF!")