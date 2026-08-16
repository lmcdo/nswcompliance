#!/usr/bin/env python3
"""
Extract PDF page images for ALL Key Sites Map provisions
from Inner West LEP 2022 (both Part 4 and Part 6)
"""

import fitz  # PyMuPDF
from pathlib import Path

# Map ALL Key Sites clause numbers to page numbers
KEY_SITES_CLAUSES = {
    # Part 4 - General Key Sites controls
    '4.3C': (39, 'pages_1_50'),  # Height of buildings on land identified as "Key sites"
    '4.4': (40, 'pages_1_50'),   # Floor space ratio

    # Part 6 - Site-specific Key Sites
    '6.14': (73, 'pages_51_100'),  # Development of land at 145–155 Parramatta Road, Annandale
    '6.15': (73, 'pages_51_100'),  # Development of land at 168–172 and 185 Parramatta Road, Annandale
    '6.16': (74, 'pages_51_100'),
    '6.17': (75, 'pages_51_100'),
    '6.18': (76, 'pages_51_100'),
    '6.19': (76, 'pages_51_100'),
    '6.21': (78, 'pages_51_100'),
    '6.22': (79, 'pages_51_100'),
    '6.23': (79, 'pages_51_100'),
    '6.24': (80, 'pages_51_100'),
    '6.25': (81, 'pages_51_100'),
    '6.27': (83, 'pages_51_100'),
    '6.30': (85, 'pages_51_100'),
    '6.31': (86, 'pages_51_100'),
    '6.34': (88, 'pages_51_100')
}

def extract_page_image(pdf_path: str, page_num: int, pdf_start_page: int, output_path: str):
    """Extract a single page as PNG at 2x resolution"""
    doc = fitz.open(pdf_path)

    # Convert page number to 0-indexed relative to PDF start
    page_index = page_num - pdf_start_page

    if page_index < 0 or page_index >= len(doc):
        print(f"[ERROR] Page {page_num} out of range for PDF (index {page_index}, total pages {len(doc)})")
        doc.close()
        return False

    page = doc[page_index]

    # Render at 2x resolution for clarity
    mat = fitz.Matrix(2, 2)
    pix = page.get_pixmap(matrix=mat)

    # Save as PNG
    pix.save(output_path)
    print(f"[OK] Extracted page {page_num} -> {Path(output_path).name} ({pix.width}x{pix.height} pixels)")

    doc.close()
    return True

def main():
    base_path = Path("../extraction_outputs/leps")

    # PDF sources
    pdfs = {
        'pages_1_50': {
            'path': base_path / "Inner West Local Environmental Plan 2022 - NSW Legislation-1-50/auto/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50_origin.pdf",
            'start_page': 1
        },
        'pages_51_100': {
            'path': base_path / "Inner West Local Environmental Plan 2022 - NSW Legislation-51-100/auto/Inner West Local Environmental Plan 2022 - NSW Legislation-51-100_origin.pdf",
            'start_page': 51
        }
    }

    # Output directory
    output_dir = Path("../frontend-nextjs/public/pdf-pages")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Verify PDFs exist
    for pdf_name, pdf_info in pdfs.items():
        if not pdf_info['path'].exists():
            print(f"[ERROR] PDF not found: {pdf_info['path']}")
            return

    # Track unique pages to avoid duplicate extraction
    pages_extracted = {}  # (page_num, pdf_name) -> output_path

    for clause, (page_num, pdf_name) in KEY_SITES_CLAUSES.items():
        # Check if this exact page from this PDF was already extracted
        page_key = (page_num, pdf_name)

        # Create output filename
        output_filename = f"iwlep_clause_{clause.replace('.', '_')}_page_{page_num}.png"
        output_path = output_dir / output_filename

        # Skip if this exact page already extracted
        if page_key in pages_extracted:
            print(f"[SKIP] Clause {clause} (page {page_num}) - duplicate of clause {pages_extracted[page_key]}")
            continue

        # Extract page
        pdf_info = pdfs[pdf_name]
        if extract_page_image(
            str(pdf_info['path']),
            page_num,
            pdf_info['start_page'],
            str(output_path)
        ):
            pages_extracted[page_key] = clause

    print(f"\n[DONE] Extracted {len(pages_extracted)} unique pages for {len(KEY_SITES_CLAUSES)} clauses")

if __name__ == "__main__":
    main()
