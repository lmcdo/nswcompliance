#!/usr/bin/env python3
"""
Extract PDF page images for SEPP (Sustainable Buildings) 2022.
Updates regulatory_provisions table with pdf_page_image_url.
"""

import os
import sys
from pathlib import Path

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    print("ERROR: pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

from dotenv import load_dotenv
import psycopg2

# Load environment
load_dotenv()
load_dotenv(Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local')

DATABASE_URL = os.getenv('DATABASE_URL')

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / 'frontend-nextjs' / 'public' / 'pdf-pages' / 'sepp-sustainable-buildings'

# SEPP Sustainable Buildings PDF
PDF_PATH = Path(__file__).parent.parent / 'extraction_outputs' / 'sepps' / 'State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation' / 'auto' / 'State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation_layout.pdf'

def get_unique_pages():
    """Get unique page numbers from database provisions."""
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return []

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT pdf_page
        FROM regulatory_provisions
        WHERE document_id LIKE '%Sustainable_Buildings%'
        AND pdf_page IS NOT NULL
        ORDER BY pdf_page
    """)

    pages = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()

    return pages

def extract_pages(pdf_path: Path, pages: list, output_dir: Path, resolution: int = 150):
    """Extract specific pages using pdfplumber."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in pages:
            if page_num <= len(pdf.pages):
                page = pdf.pages[page_num - 1]  # 0-indexed
                img = page.to_image(resolution=resolution)
                output_path = output_dir / f"sepp-sustainable-buildings_page_{page_num}.png"
                img.save(output_path)
                print(f"Extracted page {page_num} -> {output_path.name}")
            else:
                print(f"WARNING: Page {page_num} out of range (PDF has {len(pdf.pages)} pages)")

def update_database(pages: list):
    """Update regulatory_provisions with pdf_page_image_url."""
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not set")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # Update provisions for each page
        updated = 0
        for page_num in pages:
            url = f"/pdf-pages/sepp-sustainable-buildings/sepp-sustainable-buildings_page_{page_num}.png"

            cur.execute("""
                UPDATE regulatory_provisions
                SET pdf_page_image_url = %s
                WHERE document_id LIKE '%Sustainable_Buildings%'
                AND pdf_page = %s
                AND pdf_page_image_url IS NULL
            """, (url, page_num))

            count = cur.rowcount
            updated += count
            if count > 0:
                print(f"Updated {count} provisions for page {page_num}")

        conn.commit()
        print(f"\nDatabase updated: {updated} provisions total")

    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
    finally:
        cur.close()
        conn.close()

def main():
    print("=" * 70)
    print("SEPP (Sustainable Buildings) 2022 PDF Page Extraction")
    print("=" * 70)

    # Check if PDF exists
    if not PDF_PATH.exists():
        print(f"\nPDF not found at: {PDF_PATH}")
        return

    # Step 1: Get unique pages from database
    print("\n[1/3] Getting page numbers from database...")
    pages = get_unique_pages()

    if not pages:
        print("No provisions found in database with page numbers")
        return

    print(f"Found {len(pages)} unique pages: {min(pages)}-{max(pages)}")

    # Step 2: Extract page images
    print("\n[2/3] Extracting page images...")
    extract_pages(PDF_PATH, pages, OUTPUT_DIR)

    # Step 3: Update database
    print("\n[3/3] Updating database...")
    update_database(pages)

    print("\n" + "=" * 70)
    print("COMPLETE!")
    print(f"Images saved to: {OUTPUT_DIR}")
    print("=" * 70)

if __name__ == "__main__":
    main()
