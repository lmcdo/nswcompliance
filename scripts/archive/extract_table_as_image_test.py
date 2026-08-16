#!/usr/bin/env python3
"""
Test: Extract a single DCP table as an image
This will extract ONE table from the database and save it as an image
"""
import fitz  # PyMuPDF
import psycopg2
from pathlib import Path
import re

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")
IMAGE_OUTPUT = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\frontend-nextjs\public\images\dcp")

def find_pdf_for_document(document_id: str) -> Path:
    """Find the PDF file for a document_id"""
    # Search for PDFs matching this document
    for pdf_path in OUTPUT_DIR.rglob("*_origin.pdf"):
        doc_name = pdf_path.parent.parent.name
        # Normalize document name to match document_id
        normalized = doc_name.replace(' ', '_').replace('-', '_').replace('(', '_').replace(')', '_')
        normalized = re.sub(r'_+', '_', normalized)

        if document_id in normalized or normalized in document_id:
            return pdf_path
    return None

def extract_table_as_image(provision_id: int):
    """Extract a single table as an image"""

    # Get provision from database
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, document_id, pdf_page, pdf_source_file, section_header, provision_text
        FROM regulatory_provisions
        WHERE id = %s
    """, (provision_id,))

    result = cur.fetchone()

    if not result:
        print(f"[ERROR] Provision {provision_id} not found")
        return None

    prov_id, doc_id, page_num, pdf_file, section_header, provision_text = result

    print(f"Provision ID: {prov_id}")
    print(f"Document: {doc_id}")
    print(f"Page: {page_num}")
    print(f"Section: {section_header}")
    print()

    # Find PDF file
    pdf_path = find_pdf_for_document(doc_id)

    if not pdf_path or not pdf_path.exists():
        print(f"[ERROR] PDF not found for {doc_id}")
        return None

    print(f"[OK] Found PDF: {pdf_path.name}")
    print()

    # Open PDF and extract page as image
    doc = fitz.open(pdf_path)

    if page_num > len(doc):
        print(f"[ERROR] Page {page_num} not in PDF (only {len(doc)} pages)")
        return None

    # Get the page (0-indexed)
    page = doc[page_num - 1]

    # Render page as image at high resolution
    zoom = 2.0  # 2x resolution for clarity
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Save image
    IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)
    image_path = IMAGE_OUTPUT / f"provision_{prov_id}_page_{page_num}.png"
    pix.save(str(image_path))

    print(f"[OK] Image saved: {image_path}")
    print()
    print(f"Image dimensions: {pix.width}x{pix.height}")
    print(f"File size: {image_path.stat().st_size / 1024:.1f} KB")

    doc.close()
    cur.close()
    conn.close()

    return image_path

if __name__ == "__main__":
    print("=" * 70)
    print("TEST: Extract Single Table as Image")
    print("=" * 70)
    print()

    # Use provision 74802 (the setback table from Solar Access section)
    test_provision_id = 74802

    print(f"Testing with provision ID: {test_provision_id}")
    print()

    result_path = extract_table_as_image(test_provision_id)

    if result_path:
        print()
        print("=" * 70)
        print("SUCCESS!")
        print("=" * 70)
        print(f"Image path: {result_path}")
        print()
        print("Open this path in Windows Explorer to view the image:")
        print(f"  {result_path.parent}")
    else:
        print()
        print("=" * 70)
        print("FAILED")
        print("=" * 70)
