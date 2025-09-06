# 📚 Systematic Review Extractor - Complete User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [How It Works](#how-it-works)
3. [Step-by-Step Tutorial](#step-by-step-tutorial)
4. [Understanding Your Results](#understanding-your-results)
5. [Customization Guide](#customization-guide)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Getting Started

### What This Tool Does

This tool automatically extracts data from research PDFs with 100% traceability. Every piece of data extracted includes:
- A screenshot showing exactly where it came from
- The precise coordinates in the PDF
- A verification hash to ensure data integrity
- The surrounding context

### Installation (One-Time Setup)

1. **Download the tool**:
   ```bash
   # If you have the files already, skip this
   cd systematic-review-extractor
   ```

2. **Set up Python environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install required packages**:
   ```bash
   pip install PyMuPDF pillow numpy pandas flask flask-cors
   ```

## How It Works

### The Magic Behind Zero Hallucination

```
Your PDF → Pattern Matching → Coordinate Tracking → Screenshot Capture → Verified Data
```

1. **Pattern Matching**: Searches for data using regex patterns
2. **Coordinate Tracking**: Records exact [x,y] location in PDF
3. **Screenshot Capture**: Takes picture with yellow highlighting
4. **Verification**: Creates hash to ensure data wasn't modified

## Step-by-Step Tutorial

### Example 1: Basic Extraction

Let's extract data from a research paper:

```bash
python systematic_review_pipeline.py my_paper.pdf
```

**What happens:**
1. Creates a project folder with timestamp
2. Extracts all recognizable data patterns
3. Takes screenshots of every extraction
4. Generates HTML report
5. Opens report in your browser

### Example 2: Using a Medical Template

For a randomized controlled trial:

```bash
python systematic_review_pipeline.py clinical_trial.pdf --template templates/medical_rct_template.json --project my_rct_study
```

**This extracts:**
- Sample sizes (total, intervention, control)
- Age and demographics
- P-values and confidence intervals
- Mortality rates
- Adverse events
- Effect sizes

### Example 3: Custom Extraction

Create your own template file `my_patterns.json`:

```json
{
  "treatment_duration": [
    "(\\d+)\\s*weeks?\\s*of\\s*treatment",
    "treated\\s*for\\s*(\\d+)\\s*weeks?"
  ],
  "dosage": [
    "(\\d+)\\s*mg",
    "(\\d+)\\s*mg/kg"
  ]
}
```

Use it:
```bash
python systematic_review_pipeline.py paper.pdf --template my_patterns.json
```

## Understanding Your Results

### The HTML Report

When you open the HTML report, you'll see:

#### Summary Section
- **Total Extractions**: How many data points were found
- **Pages Analyzed**: Number of PDF pages processed
- **Unique Fields**: Different types of data found
- **Average Confidence**: Overall extraction quality

#### Key Findings Section
Shows the most important extracted data:
- Sample sizes
- Statistical values
- Clinical outcomes
- Each with page number and confidence score

#### Evidence Section
For each extraction:
- The exact value found
- Which page it's on
- Screenshot with yellow highlight
- Coordinates for verification

### The File Structure

```
your_project/
├── input/
│   └── your_paper.pdf           # Original PDF
├── output/
│   ├── screenshots/              # Visual evidence
│   │   ├── p1_sample_size_*.png # Page 1, sample size
│   │   └── p3_p_value_*.png     # Page 3, p-value
│   ├── json/
│   │   ├── raw_extractions.json # All data
│   │   └── analysis.json        # Organized results
│   └── reports/
│       └── extraction_report.html # Your main report
```

### Reading the JSON Output

The `raw_extractions.json` contains entries like:

```json
{
  "field": "sample_size",
  "value": "250",
  "page": 3,
  "coordinates": [123.4, 456.7, 189.0, 470.2],
  "exact_match": "n = 250",
  "screenshot": "output/screenshots/p3_sample_size_145623.png",
  "confidence": 0.9,
  "verification_hash": "a7b3c9d2f8e4"
}
```

## Customization Guide

### Common Patterns to Add

#### For Drug Studies
```json
{
  "drug_name": [
    "([A-Z][a-z]+(?:mab|nib|cept|ximab))",
    "study\\s*drug\\s*([A-Z0-9-]+)"
  ],
  "dose": [
    "(\\d+)\\s*mg(?:/kg)?",
    "(\\d+)\\s*μg"
  ]
}
```

#### For Diagnostic Studies
```json
{
  "sensitivity": [
    "sensitivity\\s*(?:was\\s*)?([\\d.]+)%?"
  ],
  "specificity": [
    "specificity\\s*(?:was\\s*)?([\\d.]+)%?"
  ],
  "auc": [
    "AUC\\s*(?:was\\s*)?([\\d.]+)",
    "area\\s*under\\s*(?:the\\s*)?curve\\s*(?:was\\s*)?([\\d.]+)"
  ]
}
```

### Adjusting Confidence Thresholds

In your code, you can filter by confidence:

```python
# Only use high-confidence extractions
high_confidence = [e for e in results['extractions'] if e['confidence'] > 0.8]
```

## Troubleshooting

### Common Issues and Solutions

#### "No extractions found"
- **Cause**: PDF might be scanned/image-based
- **Solution**: The tool works best with text-based PDFs

#### "Low confidence scores"
- **Cause**: Unusual formatting in PDF
- **Solution**: Add custom patterns matching your PDF's style

#### "Screenshots not showing highlights"
- **Cause**: Text might be in tables or figures
- **Solution**: System still extracts but highlighting works best on regular text

### Getting Better Results

1. **Use specific templates**: Choose the template matching your study type
2. **Add custom patterns**: Tailor patterns to your specific PDFs
3. **Check the JSON**: Raw data might have more than what's in the summary

## Best Practices

### For Systematic Reviews

1. **Create a template for your review**:
   - Identify key data points you need
   - Write patterns for each
   - Test on a few papers first

2. **Batch process papers**:
   ```bash
   for pdf in *.pdf; do
     python systematic_review_pipeline.py "$pdf" --template my_review_template.json
   done
   ```

3. **Combine results**:
   - All JSON files can be merged
   - Import into Excel or statistical software
   - Use for meta-analysis

### For Quality Control

1. **Always verify critical values**:
   - Check screenshots for context
   - Verify using coordinates
   - Compare with original PDF

2. **Document your process**:
   - Save your templates
   - Keep extraction reports
   - Note any manual corrections

### For Reproducibility

1. **Share your templates**: Others can reproduce your extraction
2. **Include verification hashes**: Proves data wasn't modified
3. **Archive screenshots**: Visual evidence of all extractions

## Advanced Usage

### Processing Multiple PDFs

```python
import glob
from systematic_review_pipeline import SystematicReviewPipeline

# Process all PDFs in a folder
for pdf_file in glob.glob("papers/*.pdf"):
    pipeline = SystematicReviewPipeline()
    results = pipeline.run_complete_pipeline(
        pdf_path=pdf_file,
        template_path="my_template.json"
    )
    print(f"Processed: {pdf_file}")
```

### Combining Results

```python
import json
import pandas as pd

# Load all results
all_data = []
for json_file in glob.glob("*/output/json/raw_extractions.json"):
    with open(json_file) as f:
        data = json.load(f)
        all_data.extend(data['extractions'])

# Convert to DataFrame
df = pd.DataFrame(all_data)
df.to_csv("all_extractions.csv", index=False)
```

## Tips for Success

### 🎯 Getting the Most from Your Extractions

1. **Start with built-in templates** - They cover most common patterns
2. **Review the first extraction carefully** - Ensures patterns are working
3. **Use screenshots for verification** - Visual proof prevents errors
4. **Keep confidence scores in mind** - Higher is more reliable
5. **Save your custom templates** - Reuse for similar papers

### 📊 For Meta-Analysis

- Export JSON data for statistical software
- Use confidence scores to weight extractions
- Screenshots provide evidence for PRISMA flow diagrams
- Verification hashes ensure data integrity

### 🔍 For Regulatory Submissions

- Complete audit trail for every data point
- Screenshots serve as supporting documentation
- Verification hashes prove no data manipulation
- HTML reports for reviewer-friendly format

---

## Quick Command Reference

```bash
# Basic extraction
python systematic_review_pipeline.py paper.pdf

# With medical RCT template
python systematic_review_pipeline.py paper.pdf --template templates/medical_rct_template.json

# With surgical outcomes template
python systematic_review_pipeline.py paper.pdf --template templates/surgical_outcomes_template.json

# Custom project name
python systematic_review_pipeline.py paper.pdf --project my_study

# Don't auto-open report
python systematic_review_pipeline.py paper.pdf --no-open

# With custom template
python systematic_review_pipeline.py paper.pdf --template my_patterns.json
```

---

**Remember**: Every extraction is 100% traceable to its source. No hallucination possible!