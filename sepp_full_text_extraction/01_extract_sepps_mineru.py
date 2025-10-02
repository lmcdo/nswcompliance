"""
STEP 1: Extract all SEPP PDFs using MinerU for full text extraction

Requirements:
- magic-pdf (MinerU) installed
- SEPP PDFs in docs/sepps/
- Write access to docs/sepps/extracted/

Output:
- Full markdown files in docs/sepps/extracted/
- extraction_metadata.json with extraction logs
- Verification report showing file sizes and completeness

Exit Codes:
- 0: Success - all SEPPs extracted and verified
- 1: Failure - missing PDFs or extraction errors
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import hashlib

# Configuration
SEPP_DIR = Path("../docs/sepps")
OUTPUT_DIR = SEPP_DIR / "extracted"
METADATA_FILE = OUTPUT_DIR / "extraction_metadata.json"

# Expected SEPPs (from database analysis)
EXPECTED_SEPPS = [
    "State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Planning Systems) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Housing) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Resilience and Hazards) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Industry and Employment) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Primary Production) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.pdf",  # ADDED - was missing!
]

# Minimum expected sizes (based on PDF sizes)
MIN_EXTRACTED_SIZE = {
    "Sustainable Buildings": 500_000,  # 723KB PDF should yield ~500KB+ markdown
    "Transport and Infrastructure": 100_000,  # 133KB PDF
    "Planning Systems": 1_000_000,  # 1.4MB PDF
    "Housing": 2_000_000,  # 2.6MB PDF
    "Biodiversity and Conservation": 2_000_000,  # 2.8MB PDF
    "Resilience and Hazards": 500_000,  # 685KB PDF
    "Industry and Employment": 800_000,  # 1.1MB PDF
    "Primary Production": 600_000,  # 866KB PDF
    "Exempt and Complying Development Codes": 15_000_000,  # 21MB PDF - LARGEST!
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
        print(f"X SEPP directory not found: {SEPP_DIR}")
        return False
    print(f"OK SEPP directory exists: {SEPP_DIR}")

    # Check for SEPP PDFs
    missing_pdfs = []
    found_pdfs = []
    for sepp_pdf in EXPECTED_SEPPS:
        pdf_path = SEPP_DIR / sepp_pdf
        if pdf_path.exists():
            found_pdfs.append(sepp_pdf)
            size_mb = pdf_path.stat().st_size / 1_000_000
            print(f"OK Found: {sepp_pdf} ({size_mb:.2f} MB)")
        else:
            missing_pdfs.append(sepp_pdf)
            print(f"X Missing: {sepp_pdf}")

    if missing_pdfs:
        print(f"\n[X] Missing {len(missing_pdfs)} SEPP PDFs")
        return False

    print(f"\n[OK] All {len(found_pdfs)} SEPP PDFs found")

    # Check magic-pdf is installed
    try:
        result = subprocess.run(['magic-pdf', '--version'],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"[OK] magic-pdf installed: {result.stdout.strip()}")
        else:
            print(f"[X] magic-pdf not working properly")
            return False
    except FileNotFoundError:
        print("[X] magic-pdf not installed. Install with: pip install magic-pdf")
        return False
    except Exception as e:
        print(f"[X] Error checking magic-pdf: {e}")
        return False

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Output directory ready: {OUTPUT_DIR}")

    print("\n[SUCCESS] All prerequisites met\n")
    return True

def extract_single_sepp(pdf_path, output_dir):
    """Extract single SEPP PDF with MinerU"""
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
        "expected_min_size": MIN_EXTRACTED_SIZE.get(sepp_key, 100_000),
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "error": None,
    }

    # Prepare output directory for this SEPP
    sepp_output_dir = output_dir / pdf_name.replace(".pdf", "")
    sepp_output_dir.mkdir(exist_ok=True)

    try:
        # Run MinerU extraction
        # Options: -p (pdf path), -o (output dir), -m (mode: auto/txt/ocr)
        cmd = [
            "magic-pdf",
            "-p", str(pdf_path),
            "-o", str(sepp_output_dir),
            "-m", "auto"  # Auto-detect best extraction method
        ]

        print(f"Running: {' '.join(cmd)}")
        print(f"Output: {sepp_output_dir}")
        print("(This may take 1-5 minutes per SEPP...)\n")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per SEPP
        )

        if result.returncode != 0:
            extraction_result["error"] = f"Exit code {result.returncode}: {result.stderr[:500]}"
            print(f"[X] Extraction failed: {extraction_result['error']}")
            return extraction_result

        # Find generated markdown file
        md_files = list(sepp_output_dir.glob("**/*.md"))
        if not md_files:
            extraction_result["error"] = "No markdown file generated"
            print(f"[X] No markdown output found in {sepp_output_dir}")
            return extraction_result

        # Use the largest markdown file (usually the main content)
        md_file = max(md_files, key=lambda p: p.stat().st_size)

        # Verify extraction
        md_size = md_file.stat().st_size
        extraction_result["output_file"] = str(md_file)
        extraction_result["output_size"] = md_size
        extraction_result["output_hash"] = calculate_file_hash(md_file)

        # Check minimum size
        min_size = extraction_result["expected_min_size"]
        if md_size < min_size:
            extraction_result["warning"] = f"Output size ({md_size:,} bytes) below expected minimum ({min_size:,} bytes)"
            print(f"[!] Warning: {extraction_result['warning']}")

        # Read and verify content
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            extraction_result["char_count"] = len(content)
            extraction_result["word_count"] = len(content.split())
            extraction_result["line_count"] = content.count('\n')

            # Check for key SEPP elements
            checks = {
                "has_chapter_markers": "Chapter" in content or "CHAPTER" in content,
                "has_clause_markers": "Clause" in content or content.count("(1)") > 5,
                "has_definitions": "definition" in content.lower() or "means" in content.lower(),
                "has_objectives": "objective" in content.lower() or "aim" in content.lower(),
                "not_just_header": len(content) > 10_000,  # More than just document header
            }
            extraction_result["content_checks"] = checks

            # Store first 1000 chars as preview
            extraction_result["preview"] = content[:1000]

            # Overall success check
            if all(checks.values()):
                extraction_result["success"] = True
                print(f"[OK] Extraction successful!")
            else:
                failed_checks = [k for k, v in checks.items() if not v]
                extraction_result["error"] = f"Content checks failed: {failed_checks}"
                print(f"[X] Content verification failed: {failed_checks}")

        # Print summary
        print(f"\nExtraction Summary:")
        print(f"  PDF Size:      {extraction_result['pdf_size']:>12,} bytes")
        print(f"  Output Size:   {md_size:>12,} bytes")
        print(f"  Characters:    {extraction_result['char_count']:>12,}")
        print(f"  Words:         {extraction_result['word_count']:>12,}")
        print(f"  Lines:         {extraction_result['line_count']:>12,}")
        print(f"  Status:        {'[OK] SUCCESS' if extraction_result['success'] else '[X] FAILED'}")

        return extraction_result

    except subprocess.TimeoutExpired:
        extraction_result["error"] = "Extraction timeout after 10 minutes"
        print(f"[X] Timeout error")
        return extraction_result
    except Exception as e:
        extraction_result["error"] = str(e)
        print(f"[X] Unexpected error: {e}")
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
    print("SEPP FULL TEXT EXTRACTION - STEP 1")
    print("="*80 + "\n")

    # Check prerequisites
    if not check_prerequisites():
        print("\n[X] Prerequisites check failed. Cannot proceed.")
        return 1

    # Extract all SEPPs
    results = []
    for sepp_pdf in EXPECTED_SEPPS:
        pdf_path = SEPP_DIR / sepp_pdf
        result = extract_single_sepp(pdf_path, OUTPUT_DIR)
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