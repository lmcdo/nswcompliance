#!/usr/bin/env python3
"""
Extract PDF page images for Housing SEPP 2021 clauses.

Clauses needed:
- 108: Manor Houses
- 168-169: Dual Occupancy
- 172-173: Multi Dwelling Housing / Terraces
- 174-176: Residential Flat Buildings (LMR)

Usage:
1. Download SEPP Housing 2021 PDF from NSW Legislation
2. Run: python extract_housing_sepp_pages.py
"""

import os
import sys
from pathlib import Path

# Try to import pdf2image (uses poppler)
try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
    print("Warning: pdf2image not installed. Will try pdfplumber.")

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()
load_dotenv(Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / 'frontend-nextjs' / 'public' / 'pdf-pages' / 'sepp-housing'

# SEPP Housing 2021 PDF - need to download from NSW Legislation
# https://legislation.nsw.gov.au/view/pdf/asmade/epi-2021-0714
PDF_URL = "https://legislation.nsw.gov.au/view/pdf/asmade/epi-2021-0714"
PDF_PATH = Path(__file__).parent / "sepp_housing_2021.pdf"

# Clause to page mapping (need to verify from actual PDF)
# These are estimates based on typical SEPP structure - VERIFY WITH ACTUAL PDF
CLAUSE_PAGE_MAPPING = {
    # Format: clause_prefix: (estimated_page, description)
    "108": (None, "Manor Houses - Part 2 Div 1"),
    "168": (None, "Dual Occupancy - Part 4 Div 2"),
    "169": (None, "Dual Occupancy subdivision - Part 4 Div 2"),
    "172": (None, "Multi Dwelling Housing - Part 4 Div 3"),
    "173": (None, "Terraces subdivision - Part 4 Div 3"),
    "174": (None, "RFBs in R1/R2 zones - Part 4 Div 4"),
    "175": (None, "RFBs in R3/R4 inner - Part 4 Div 4"),
    "176": (None, "RFBs in R3/R4 outer - Part 4 Div 4"),
}


def find_clause_pages(pdf_path: Path) -> dict:
    """
    Search PDF for clause numbers and return page mapping.
    """
    if not HAS_PDFPLUMBER:
        print("ERROR: pdfplumber required for clause search")
        return {}

    clause_pages = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""

            # Search for clause patterns
            for clause in CLAUSE_PAGE_MAPPING.keys():
                # Look for "108 " or "Clause 108" or "108("
                patterns = [
                    f"\\b{clause}\\s+",
                    f"Clause {clause}",
                    f"\\b{clause}\\(",
                    f"Division.*{clause}"
                ]

                import re
                for pattern in patterns:
                    if re.search(pattern, text):
                        if clause not in clause_pages:
                            clause_pages[clause] = page_num
                            print(f"Found clause {clause} on page {page_num}")
                        break

            # Progress
            if page_num % 20 == 0:
                print(f"Scanned {page_num}/{len(pdf.pages)} pages...")

    return clause_pages


def extract_pages_pdf2image(pdf_path: Path, pages: list, output_dir: Path, dpi: int = 150):
    """Extract specific pages using pdf2image (poppler)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for page_num in pages:
        print(f"Extracting page {page_num}...")
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=dpi
        )

        if images:
            output_path = output_dir / f"sepp-housing_page_{page_num}.png"
            images[0].save(output_path, "PNG")
            print(f"  Saved: {output_path.name}")


def extract_pages_pdfplumber(pdf_path: Path, pages: list, output_dir: Path, resolution: int = 150):
    """Extract specific pages using pdfplumber."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in pages:
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]  # 0-indexed
                img = page.to_image(resolution=resolution)
                output_path = output_dir / f"sepp-housing_page_{page_num}.png"
                img.save(output_path)
                print(f"Extracted page {page_num} -> {output_path.name}")


def update_database(clause_pages: dict):
    """Add pdf_page_image_url column and update housing_sepp_standards."""
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Add column if not exists
        cur.execute("""
            ALTER TABLE housing_sepp_standards
            ADD COLUMN IF NOT EXISTS pdf_page INTEGER,
            ADD COLUMN IF NOT EXISTS pdf_page_image_url TEXT
        """)

        # Update each clause
        for clause, page_num in clause_pages.items():
            url = f"/pdf-pages/sepp-housing/sepp-housing_page_{page_num}.png"

            # Update all standards with this clause prefix
            cur.execute("""
                UPDATE housing_sepp_standards
                SET pdf_page = %s, pdf_page_image_url = %s
                WHERE source_clause LIKE %s
            """, (page_num, url, f"{clause}%"))

            print(f"Updated clause {clause}* -> page {page_num}")

        conn.commit()
        print("Database updated successfully!")

    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()


def main():
    print("=" * 60)
    print("SEPP Housing 2021 PDF Page Extraction")
    print("=" * 60)

    # Check if PDF exists
    if not PDF_PATH.exists():
        print(f"\nPDF not found at: {PDF_PATH}")
        print(f"\nPlease download from:")
        print(f"  {PDF_URL}")
        print(f"\nAnd save to:")
        print(f"  {PDF_PATH}")
        return

    # Step 1: Find clause pages
    print("\n[1/3] Scanning PDF for clause locations...")
    clause_pages = find_clause_pages(PDF_PATH)

    if not clause_pages:
        print("No clauses found. Check PDF format.")
        return

    print(f"\nFound {len(clause_pages)} clauses:")
    for clause, page in sorted(clause_pages.items()):
        print(f"  Clause {clause}: page {page}")

    # Step 2: Extract page images
    print("\n[2/3] Extracting page images...")
    pages_to_extract = list(set(clause_pages.values()))

    # Use pdfplumber (more reliable on Windows)
    if HAS_PDFPLUMBER:
        extract_pages_pdfplumber(PDF_PATH, pages_to_extract, OUTPUT_DIR)
    elif HAS_PDF2IMAGE:
        extract_pages_pdf2image(PDF_PATH, pages_to_extract, OUTPUT_DIR)
    else:
        print("ERROR: No PDF library available")
        return

    # Step 3: Update database
    print("\n[3/3] Updating database...")
    update_database(clause_pages)

    print("\n" + "=" * 60)
    print("COMPLETE!")
    print(f"Images saved to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
