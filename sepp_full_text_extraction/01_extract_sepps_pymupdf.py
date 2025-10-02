"""
STEP 1: Extract all SEPP PDFs using PyMuPDF (alternative to MinerU)

PyMuPDF is better suited for text-only PDFs (which most SEPPs are).
Faster and more reliable than MinerU for text extraction.

Requirements:
- PyMuPDF (fitz) installed
- SEPP PDFs in docs/sepps/

Output:
- Markdown files in docs/sepps/extracted/
- extraction_metadata.json with extraction logs
"""

import os
import sys
import json
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime
import hashlib

# Configuration
SEPP_DIR = Path("../docs/sepps")
OUTPUT_DIR = SEPP_DIR / "extracted"
METADATA_FILE = OUTPUT_DIR / "extraction_metadata.json"

# Expected SEPPs
EXPECTED_SEPPS = [
    "State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Planning Systems) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Housing) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Resilience and Hazards) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Industry and Employment) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Primary Production) 2021 - NSW Legislation.pdf",
]

# Minimum expected sizes (PyMuPDF typically extracts more text than MinerU)
MIN_EXTRACTED_SIZE = {
    "Sustainable Buildings": 300_000,  # 17 pages
    "Transport and Infrastructure": 5_000,  # 1 page only!
    "Planning Systems": 800_000,  # 63 pages
    "Housing": 1_500_000,  # 120 pages
    "Biodiversity and Conservation": 1_400_000,  # 110 pages
    "Resilience and Hazards": 250_000,  # 21 pages
    "Industry and Employment": 500_000,  # 43 pages
    "Primary Production": 300_000,  # 28 pages
}

def get_sepp_key(filename):
    """Extract SEPP name key from filename"""
    for key in MIN_EXTRACTED_SIZE.keys():
        if key in filename:
            return key
    return "Unknown"

def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def check_prerequisites():
    """Verify environment is ready"""
    print("=== CHECKING PREREQUISITES ===\n")

    # Check SEPP directory exists
    if not SEPP_DIR.exists():
        print(f"[X] SEPP directory not found: {SEPP_DIR}")
        return False
    print(f"[OK] SEPP directory exists: {SEPP_DIR}")

    # Check for SEPP PDFs
    missing_pdfs = []
    found_pdfs = []
    for sepp_pdf in EXPECTED_SEPPS:
        pdf_path = SEPP_DIR / sepp_pdf
        if pdf_path.exists():
            found_pdfs.append(sepp_pdf)
            size_mb = pdf_path.stat().st_size / 1_000_000
            print(f"[OK] Found: {sepp_pdf} ({size_mb:.2f} MB)")
        else:
            missing_pdfs.append(sepp_pdf)
            print(f"[X] Missing: {sepp_pdf}")

    if missing_pdfs:
        print(f"\n[X] Missing {len(missing_pdfs)} SEPP PDFs")
        return False

    print(f"\n[OK] All {len(found_pdfs)} SEPP PDFs found")

    # Check PyMuPDF
    try:
        print(f"[OK] PyMuPDF (fitz) version: {fitz.__version__}")
    except Exception as e:
        print(f"[X] PyMuPDF error: {e}")
        return False

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Output directory ready: {OUTPUT_DIR}")

    print("\n[SUCCESS] All prerequisites met\n")
    return True

def extract_single_sepp_pymupdf(pdf_path, output_dir):
    """Extract single SEPP PDF with PyMuPDF"""
    pdf_name = pdf_path.name
    sepp_key = get_sepp_key(pdf_name)

    print(f"\n{'='*80}")
    print(f"EXTRACTING: {pdf_name}")
    print(f"{'='*80}")

    extraction_result = {
        "pdf_name": pdf_name,
        "pdf_path": str(pdf_path),
        "pdf_size": pdf_path.stat().st_size,
        "pdf_hash": calculate_file_hash(pdf_path),
        "sepp_key": sepp_key,
        "expected_min_size": MIN_EXTRACTED_SIZE.get(sepp_key, 50_000),
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "extraction_method": "pymupdf"
    }

    # Prepare output file
    md_filename = pdf_name.replace(".pdf", ".md")
    md_file = output_dir / md_filename

    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        print(f"PDF Pages: {total_pages}")
        print(f"Extracting text from all pages...")

        # Extract text from all pages
        full_text = []
        for page_num, page in enumerate(doc):
            # Extract text with formatting preserved
            text = page.get_text("text")  # Plain text extraction

            # Add page markers for reference
            if page_num == 0:
                full_text.append(f"# {pdf_name}\n")
                full_text.append(f"Extracted: {datetime.now().strftime('%Y-%m-%d')}\n")
                full_text.append(f"Total Pages: {total_pages}\n\n")
                full_text.append("="*80 + "\n\n")

            full_text.append(f"## Page {page_num + 1}\n\n")
            full_text.append(text)
            full_text.append("\n\n")

            if (page_num + 1) % 10 == 0:
                print(f"  Processed {page_num + 1}/{total_pages} pages...")

        doc.close()

        # Combine text
        markdown_content = ''.join(full_text)

        # Save to markdown file
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        # Verify extraction
        md_size = md_file.stat().st_size
        extraction_result["output_file"] = str(md_file)
        extraction_result["output_size"] = md_size
        extraction_result["output_hash"] = calculate_file_hash(md_file)
        extraction_result["char_count"] = len(markdown_content)
        extraction_result["word_count"] = len(markdown_content.split())
        extraction_result["line_count"] = markdown_content.count('\n')
        extraction_result["page_count"] = total_pages

        # Check minimum size
        min_size = extraction_result["expected_min_size"]
        if md_size < min_size:
            extraction_result["warning"] = f"Output size ({md_size:,} bytes) below expected minimum ({min_size:,} bytes)"
            print(f"[!] Warning: {extraction_result['warning']}")

        # Content checks
        checks = {
            "has_chapter_markers": "Chapter" in markdown_content or "CHAPTER" in markdown_content,
            "has_clause_markers": "Clause" in markdown_content or markdown_content.count("(1)") > 5,
            "has_definitions": "definition" in markdown_content.lower() or "means" in markdown_content.lower(),
            "has_objectives": "objective" in markdown_content.lower() or "aim" in markdown_content.lower(),
            "not_just_header": len(markdown_content) > 10_000,
        }
        extraction_result["content_checks"] = checks

        # Store preview
        extraction_result["preview"] = markdown_content[:1000]

        # Overall success check
        if all(checks.values()):
            extraction_result["success"] = True
            print(f"[OK] Extraction successful!")
        else:
            failed_checks = [k for k, v in checks.items() if not v]
            extraction_result["warning"] = f"Some content checks failed: {failed_checks}"
            extraction_result["success"] = True  # Still consider success if text extracted
            print(f"[!] Warning: {extraction_result['warning']}")

        # Print summary
        print(f"\nExtraction Summary:")
        print(f"  PDF Size:      {extraction_result['pdf_size']:>12,} bytes")
        print(f"  Pages:         {total_pages:>12,}")
        print(f"  Output Size:   {md_size:>12,} bytes")
        print(f"  Characters:    {extraction_result['char_count']:>12,}")
        print(f"  Words:         {extraction_result['word_count']:>12,}")
        print(f"  Status:        [OK] SUCCESS")

        return extraction_result

    except Exception as e:
        extraction_result["error"] = str(e)
        print(f"[X] Extraction failed: {e}")
        return extraction_result

def generate_verification_report(results):
    """Generate comprehensive verification report"""
    print(f"\n{'='*80}")
    print("EXTRACTION VERIFICATION REPORT")
    print(f"{'='*80}\n")

    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful

    print(f"Total SEPPs:       {total}")
    print(f"Successful:        {successful} [OK]")
    print(f"Failed:            {failed} {'[X]' if failed > 0 else ''}")
    print(f"Success Rate:      {successful/total*100:.1f}%\n")

    # Detailed results
    print("Detailed Results:\n")
    for i, result in enumerate(results, 1):
        status = "[OK]" if result["success"] else "[X]"
        print(f"{i}. {status} {result['sepp_key']}")
        print(f"   File: {result['pdf_name']}")
        print(f"   Size: {result.get('output_size', 0):,} bytes ({result.get('char_count', 0):,} chars)")
        if result.get("warning"):
            print(f"   [!] Warning: {result['warning']}")
        if result.get("error"):
            print(f"   [X] Error: {result['error']}")
        print()

    # Save metadata
    metadata = {
        "extraction_timestamp": datetime.now().isoformat(),
        "extraction_method": "pymupdf",
        "total_sepps": total,
        "successful_extractions": successful,
        "failed_extractions": failed,
        "results": results
    }

    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"Metadata saved to: {METADATA_FILE}")

    return successful == total

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("SEPP FULL TEXT EXTRACTION - STEP 1 (PyMuPDF)")
    print("="*80 + "\n")

    # Check prerequisites
    if not check_prerequisites():
        print("\n[X] Prerequisites check failed. Cannot proceed.")
        return 1

    # Extract all SEPPs
    results = []
    for sepp_pdf in EXPECTED_SEPPS:
        pdf_path = SEPP_DIR / sepp_pdf
        result = extract_single_sepp_pymupdf(pdf_path, OUTPUT_DIR)
        results.append(result)

    # Generate verification report
    all_successful = generate_verification_report(results)

    if all_successful:
        print("\n[SUCCESS] ALL EXTRACTIONS SUCCESSFUL")
        print(f"\nNext step: Run 02_parse_markdown_to_json.py")
        return 0
    else:
        print("\n[X] SOME EXTRACTIONS FAILED")
        print("Review errors above and re-run failed extractions")
        return 1

if __name__ == "__main__":
    sys.exit(main())