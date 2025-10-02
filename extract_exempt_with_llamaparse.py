"""
Extract "Exempt and Complying" SEPP with LlamaParse (LlamaIndex's PDF extraction)
This is the proper tool for complex nested structures
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv('.env.local')

pdf_file = Path("docs/sepps/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.pdf")
output_file = Path("docs/sepps/extracted/State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation_LLAMAPARSE.md")

if not pdf_file.exists():
    print(f"[ERROR] PDF not found: {pdf_file}")
    sys.exit(1)

print("="*80)
print("EXTRACTING WITH LLAMAPARSE (PROPER STRUCTURED EXTRACTION)")
print("="*80)
print(f"PDF: {pdf_file.name}")
print(f"Size: {pdf_file.stat().st_size / 1_000_000:.1f} MB (454 pages)")
print(f"Output: {output_file}")
print("\nLlamaParse handles:")
print("  - Nested code structures (Housing Code, Rural Housing Code, etc.)")
print("  - Multi-level provisions (2.1(a)(i))")
print("  - Tables and schedules")
print("  - Complex legal formatting")
print("\nThis may take 15-30 minutes...")
print("="*80 + "\n")

try:
    # Check if llamaparse is installed
    try:
        from llama_parse import LlamaParse
        print("[OK] llama-parse installed")
    except ImportError:
        print("[INFO] Installing llama-parse...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "llama-parse"], check=True)
        from llama_parse import LlamaParse
        print("[OK] llama-parse installed successfully")

    # Check API key
    api_key = os.getenv('LLAMA_CLOUD_API_KEY')
    if not api_key:
        print("[ERROR] LLAMA_CLOUD_API_KEY not found in .env.local")
        print("[INFO] Get your key from: https://cloud.llamaindex.ai/")
        sys.exit(1)

    print(f"[1/3] Initializing LlamaParse with API key...")
    parser = LlamaParse(
        api_key=api_key,
        result_type="markdown",  # Get markdown output
        verbose=True,
        language="en",
        parsing_instruction="""
        Extract all provisions with full structure including:
        - Main clauses (1.1, 1.2, etc.)
        - All Development Codes (Housing Code, Rural Housing Code, etc.)
        - Sub-provisions within codes (2.1(a), 2.1(b), etc.)
        - All definitions
        - All schedules

        Preserve hierarchical structure and numbering.
        """
    )

    print(f"\n[2/3] Uploading and parsing PDF (this takes time)...")
    print(f"      LlamaParse is processing 454 pages...")

    # Parse the PDF
    documents = parser.load_data(str(pdf_file))

    print(f"\n[3/3] Extraction complete!")
    print(f"      Received {len(documents)} document chunks")

    # Combine all chunks and save
    full_text = "\n\n".join([doc.text for doc in documents])

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(full_text)

    print(f"\n[OK] Saved to: {output_file}")
    print(f"     Size: {output_file.stat().st_size / 1_000_000:.2f} MB")
    print(f"     Lines: {full_text.count(chr(10)):,}")
    print(f"     Words: {len(full_text.split()):,}")

    print(f"\n[SUCCESS] Extraction complete with LlamaParse!")
    print(f"\nNext steps:")
    print(f"1. python sepp_full_text_extraction/02_parse_markdown_to_json_FIXED.py")
    print(f"2. python sepp_full_text_extraction/04_import_full_provisions_FIXED.py")

except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    print(f"\n[INFO] Install with: pip install llama-parse")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)