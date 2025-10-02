"""
Extract ONLY the "Exempt and Complying Development Codes" SEPP
(The one that was inexplicably missing from the original extraction list)
"""
import subprocess
import sys
from pathlib import Path

pdf_file = Path("docs/sepps/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.pdf")
output_dir = Path("docs/sepps/extracted/")

if not pdf_file.exists():
    print(f"[ERROR] PDF not found: {pdf_file}")
    sys.exit(1)

print("="*80)
print("EXTRACTING THE MISSING SEPP")
print("="*80)
print(f"PDF: {pdf_file.name}")
print(f"Size: {pdf_file.stat().st_size / 1_000_000:.1f} MB")
print(f"Output: {output_dir}")
print("\nThis will take 5-10 minutes for a 21MB PDF...")
print("="*80 + "\n")

# Try PyMuPDF first (faster)
try:
    import fitz  # PyMuPDF

    print("[1/2] Extracting with PyMuPDF...")
    doc = fitz.open(pdf_file)

    markdown_content = []
    markdown_content.append(f"# {pdf_file.name}")
    markdown_content.append(f"Extracted: 2025-09-30")
    markdown_content.append(f"Total Pages: {len(doc)}")
    markdown_content.append("\n" + "="*80 + "\n")

    for page_num in range(len(doc)):
        if page_num % 50 == 0:
            print(f"   Processing page {page_num + 1}/{len(doc)}...")

        page = doc[page_num]
        markdown_content.append(f"\n## Page {page_num + 1}\n")
        text = page.get_text()
        markdown_content.append(text)

    doc.close()

    # Save markdown
    output_file = output_dir / f"{pdf_file.stem}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown_content))

    print(f"\n[2/2] Saved markdown: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1_000_000:.1f} MB")
    print(f"   Lines: {len(markdown_content):,}")

    print(f"\n[SUCCESS] Extraction complete!")
    print(f"\nNext steps:")
    print(f"1. python sepp_full_text_extraction/02_parse_markdown_to_json_FIXED.py")
    print(f"2. python sepp_full_text_extraction/04_import_full_provisions_FIXED.py")

except ImportError:
    print("[WARN] PyMuPDF not installed, trying magic-pdf...")

    # Fallback to magic-pdf
    try:
        cmd = [
            "magic-pdf",
            "-p", str(pdf_file),
            "-o", str(output_dir),
            "-m", "auto"
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

        if result.returncode == 0:
            print("[SUCCESS] magic-pdf extraction complete")
        else:
            print(f"[ERROR] magic-pdf failed: {result.stderr[:200]}")
            sys.exit(1)

    except FileNotFoundError:
        print("[ERROR] Neither PyMuPDF nor magic-pdf available")
        print("Install with: pip install pymupdf")
        sys.exit(1)