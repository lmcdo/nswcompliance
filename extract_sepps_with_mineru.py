"""
Re-extract all SEPP PDFs using MinerU for full text extraction
"""
import os
import subprocess
from pathlib import Path

# SEPPs to extract
sepp_dir = Path("docs/sepps")
output_base = Path("output_sepps_full")
output_base.mkdir(exist_ok=True)

sepp_pdfs = [
    "State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Planning Systems) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Housing) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Resilience and Hazards) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Industry and Employment) 2021 - NSW Legislation.pdf",
    "State Environmental Planning Policy (Primary Production) 2021 - NSW Legislation.pdf",
]

print("=== EXTRACTING SEPPS WITH MINERU ===\n")
print("This will extract FULL TEXT from all SEPP PDFs\n")

for sepp_pdf in sepp_pdfs:
    pdf_path = sepp_dir / sepp_pdf

    if not pdf_path.exists():
        print(f"SKIP: {sepp_pdf} - File not found")
        continue

    output_dir = output_base / sepp_pdf.replace(".pdf", "")
    output_dir.mkdir(exist_ok=True)

    print(f"\nExtracting: {sepp_pdf}")
    print(f"  Output: {output_dir}")

    # Run MinerU extraction
    # Assuming magic-pdf is the MinerU command
    try:
        cmd = [
            "magic-pdf",
            "-p", str(pdf_path),
            "-o", str(output_dir),
            "-m", "auto"  # Auto-detect layout
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            # Check output size
            md_files = list(output_dir.glob("*.md"))
            if md_files:
                md_file = md_files[0]
                size = md_file.stat().st_size
                print(f"  ✓ Success: {size:,} bytes extracted")

                # Show first 500 chars to verify content
                with open(md_file, 'r', encoding='utf-8') as f:
                    preview = f.read(500)
                    print(f"  Preview: {preview[:200]}...")
            else:
                print(f"  ✗ No markdown file generated")
        else:
            print(f"  ✗ Extraction failed: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout after 5 minutes")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "="*60)
print("EXTRACTION COMPLETE")
print(f"Check {output_base}/ for full SEPP markdown files")
print("\nNext steps:")
print("1. Verify markdown files contain full text (not just headers)")
print("2. Run import script to load full text into database")
print("3. Remove 500-char truncation from import pipeline")