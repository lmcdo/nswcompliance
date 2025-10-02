"""
Extract "Exempt and Complying" SEPP using langextract
(The proper deep extraction tool, not PyMuPDF)
"""
import sys
from pathlib import Path
from langextract import extract

pdf_file = Path("docs/sepps/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.pdf")
output_file = Path("docs/sepps/extracted/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation_PROPER.md")

if not pdf_file.exists():
    print(f"[ERROR] PDF not found: {pdf_file}")
    sys.exit(1)

print("="*80)
print("EXTRACTING WITH LANGEXTRACT (PROPER DEEP EXTRACTION)")
print("="*80)
print(f"PDF: {pdf_file.name}")
print(f"Size: {pdf_file.stat().st_size / 1_000_000:.1f} MB")
print(f"Pages: 454")
print(f"\nThis will extract ALL nested structures:")
print("  - Main clauses (1.1, 1.2, etc.)")
print("  - Codes (Housing Code, Rural Housing Code, etc.)")
print("  - Sub-provisions within codes")
print("  - Definitions")
print("  - Schedules")
print("\nThis may take 10-20 minutes for a 21MB PDF...")
print("="*80 + "\n")

try:
    print("[1/3] Running langextract...")

    # Use langextract to properly extract with structure
    result = extract(
        source=str(pdf_file),
        output_file=str(output_file),
        verbose=True
    )

    print(f"\n[2/3] Extraction complete!")
    print(f"  Result type: {type(result)}")
    print(f"  Output file: {output_file}")

    if output_file.exists():
        size = output_file.stat().st_size
        print(f"  Output size: {size / 1_000_000:.2f} MB")

        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.count('\n')
            words = len(content.split())
            print(f"  Lines: {lines:,}")
            print(f"  Words: {words:,}")
            print(f"\n  First 300 chars:")
            print(f"  {content[:300]}")

        print(f"\n[3/3] Now parse with:")
        print(f"  python sepp_full_text_extraction/02_parse_markdown_to_json_FIXED.py")

    else:
        print(f"[WARN] Output file not found: {output_file}")
        print(f"[INFO] Result: {result}")

except Exception as e:
    print(f"[ERROR] Extraction failed: {e}")
    import traceback
    traceback.print_exc()

    print("\n[INFO] Trying with minimal parameters...")
    try:
        # Try simpler call
        result = extract(str(pdf_file))
        print(f"[OK] Basic extraction returned: {type(result)}")
        print(f"First 500 chars: {str(result)[:500]}")

        # Save manually
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(result))
        print(f"[OK] Saved to: {output_file}")

    except Exception as e2:
        print(f"[ERROR] Also failed: {e2}")
        sys.exit(1)