#!/usr/bin/env python3
"""
Extract PDF page images for all site-specific Part 6 clauses
from Inner West LEP 2022
"""

import fitz  # PyMuPDF
from pathlib import Path

# Map clause numbers to page numbers
CLAUSE_PAGES = {
    '6.16': 74,
    '6.17': 75,
    '6.18': 76,
    '6.19': 76,  # Same page as 6.18
    '6.20': 77,  # Already extracted
    '6.24': 80,
    '6.25': 81,
    '6.26': 83,
    '6.30': 85,
    '6.31': 86,
    '6.34': 88
}

def extract_page_image(pdf_path: str, page_num: int, output_path: str):
    """Extract a single page as PNG at 2x resolution"""
    doc = fitz.open(pdf_path)

    # Convert page number to 0-indexed
    page_index = page_num - 51  # Pages 51-100 PDF

    if page_index < 0 or page_index >= len(doc):
        print(f"Page {page_num} out of range for PDF")
        return False

    page = doc[page_index]

    # Render at 2x resolution for clarity
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)

    # Save as PNG
    pix.save(output_path)
    print(f"[OK] Extracted page {page_num} -> {output_path} ({pix.width}x{pix.height} pixels)")

    doc.close()
    return True

def main():
    # Source PDF (pages 51-100)
    pdf_path = Path("../extraction_outputs/leps/Inner West Local Environmental Plan 2022 - NSW Legislation-51-100/auto/Inner West Local Environmental Plan 2022 - NSW Legislation-51-100_origin.pdf")

    # Output directory
    output_dir = Path("../frontend-nextjs/public/pdf-pages")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    # Track unique pages to extract
    pages_extracted = set()

    for clause, page_num in CLAUSE_PAGES.items():
        # Skip if already extracted
        if page_num == 77:
            print(f"[SKIP] Clause {clause} (page {page_num}) - already extracted")
            continue

        # Skip duplicate pages
        if page_num in pages_extracted:
            print(f"[SKIP] Clause {clause} (page {page_num}) - already extracted in this run")
            continue

        # Create output filename
        output_filename = f"iwlep_site_specific_clause_{clause.replace('.', '_')}_page_{page_num}.png"
        output_path = output_dir / output_filename

        # Extract page
        if extract_page_image(str(pdf_path), page_num, str(output_path)):
            pages_extracted.add(page_num)

    print(f"\n[DONE] Extracted {len(pages_extracted)} unique pages")

if __name__ == "__main__":
    main()
