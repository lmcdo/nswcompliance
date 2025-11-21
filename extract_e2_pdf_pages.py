"""
Extract E2 Haberfield Heritage Conservation Area PDF pages as PNG images.

Based on: extract_ashfield_chapter_f_pages.py
Purpose: Convert each page of E2 PDF to PNG for display in UI
Output: frontend-nextjs/public/pdf-pages/leichhardt-e2/page_X.png
"""

import fitz  # PyMuPDF
from pathlib import Path
import sys

# Paths
PDF_PATH = "output/Chapter E2 Haberfield Neighbourhood/auto/Chapter E2 Haberfield Neighbourhood_origin.pdf"
OUTPUT_DIR = Path("frontend-nextjs/public/pdf-pages/leichhardt-e2")

def extract_pdf_pages():
    """Extract all pages from E2 PDF as PNG images"""

    # Verify PDF exists
    if not Path(PDF_PATH).exists():
        print(f"[ERROR] PDF not found at {PDF_PATH}")
        print(f"   Current directory: {Path.cwd()}")
        sys.exit(1)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[+] Created output directory: {OUTPUT_DIR}")

    # Open PDF
    doc = fitz.open(PDF_PATH)
    print(f"[+] Opened PDF: {PDF_PATH}")
    print(f"[+] Total pages: {len(doc)}")

    # Extract each page
    total_pages = len(doc)
    for page_num in range(total_pages):
        page = doc[page_num]

        # Convert to image (150 DPI for good quality)
        pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))

        # Save as PNG (page numbers start at 1 for user display)
        output_path = OUTPUT_DIR / f"page_{page_num + 1}.png"
        pix.save(output_path)

        print(f"[OK] Page {page_num + 1}: {output_path.name} ({pix.width}x{pix.height}px)")

    doc.close()

    print(f"\n[SUCCESS] Extracted {total_pages} pages to {OUTPUT_DIR}")
    print(f"\n[NEXT STEPS]")
    print(f"   1. Run map_e2_requirements_to_pdf_pages.py to map requirements -> pages")
    print(f"   2. Apply generated SQL to update database")
    print(f"   3. Test with 34 Dalhousie St, Haberfield in UI")

if __name__ == "__main__":
    extract_pdf_pages()
