"""
Extract "Exempt and Complying" SEPP using MinerU Python API
(Not PyMuPDF which can't handle the nested structure)
"""
import sys
from pathlib import Path

pdf_file = Path("docs/sepps/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.pdf")
output_dir = Path("docs/sepps/extracted_mineru")
output_dir.mkdir(exist_ok=True)

if not pdf_file.exists():
    print(f"[ERROR] PDF not found: {pdf_file}")
    sys.exit(1)

print("="*80)
print("EXTRACTING WITH MINERU (NOT PYMUPDF)")
print("="*80)
print(f"PDF: {pdf_file.name}")
print(f"Size: {pdf_file.stat().st_size / 1_000_000:.1f} MB (454 pages)")
print(f"Output: {output_dir}")
print("\nUsing MinerU for deep structure extraction...")
print("="*80 + "\n")

try:
    # Try importing MinerU
    import mineru
    print(f"[OK] MinerU module found: {mineru.__file__}")

    # Check what's available in MinerU
    print(f"[INFO] MinerU contents: {dir(mineru)[:10]}...")

    # Try to find the extraction function
    if hasattr(mineru, 'extract'):
        print("[INFO] Using mineru.extract()...")
        result = mineru.extract(str(pdf_file), str(output_dir))
        print(f"[OK] Extraction complete: {result}")
    elif hasattr(mineru, 'parse_pdf'):
        print("[INFO] Using mineru.parse_pdf()...")
        result = mineru.parse_pdf(str(pdf_file), str(output_dir))
        print(f"[OK] Extraction complete: {result}")
    else:
        print("[WARN] MinerU module doesn't have expected extract functions")
        print(f"[INFO] Available functions: {[m for m in dir(mineru) if not m.startswith('_')]}")

        # Fall back to trying langextract
        print("\n[INFO] Trying langextract instead...")
        import langextract
        print(f"[OK] langextract found: {langextract.__file__}")

        # Check langextract API
        print(f"[INFO] langextract functions: {[m for m in dir(langextract) if not m.startswith('_')]}")

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print("\n[INFO] Checking what extraction libraries are available...")

    import pkgutil
    installed = [m.name for m in pkgutil.iter_modules()]
    extraction_libs = [lib for lib in installed if any(x in lib.lower() for x in ['extract', 'pdf', 'miner', 'llama'])]
    print(f"[INFO] Found: {extraction_libs[:20]}")

    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n[SUCCESS] Check output directory for extracted files")
print(f"ls {output_dir}")