#!/usr/bin/env python3
"""
Extract all DCP provision pages as images

This creates a PDF page image for every provision, giving users
perfect fidelity reference material while keeping text searchable.
"""
import fitz  # PyMuPDF
import psycopg2
from pathlib import Path
import re
from collections import defaultdict

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
    for pdf_path in OUTPUT_DIR.rglob("*_origin.pdf"):
        doc_name = pdf_path.parent.parent.name
        normalized = doc_name.replace(' ', '_').replace('-', '_').replace('(', '_').replace(')', '_')
        normalized = re.sub(r'_+', '_', normalized)

        if document_id in normalized or normalized in document_id:
            return pdf_path
    return None


def extract_all_page_images():
    """Extract page images for all DCP provisions"""

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get all DCP provisions
    cur.execute("""
        SELECT id, document_id, pdf_page, section_header
        FROM regulatory_provisions
        WHERE (document_id LIKE '%Marrickville%'
            OR document_id LIKE '%Ashfield%'
            OR document_id LIKE '%Leichhardt%')
            AND pdf_page IS NOT NULL
        ORDER BY document_id, pdf_page;
    """)

    provisions = cur.fetchall()

    print(f"Found {len(provisions)} provisions to process")
    print()

    # Group by document to minimize PDF opens
    by_document = defaultdict(list)
    for prov_id, doc_id, page_num, section_header in provisions:
        by_document[doc_id].append({
            'id': prov_id,
            'page': page_num,
            'section': section_header
        })

    print(f"Grouped into {len(by_document)} documents")
    print()

    # Create image directory
    IMAGE_OUTPUT.mkdir(parents=True, exist_ok=True)

    total_extracted = 0
    total_failed = 0
    total_size_mb = 0

    # Process each document
    for idx, (doc_id, provisions_list) in enumerate(by_document.items(), start=1):
        print(f"[{idx}/{len(by_document)}] {doc_id}")

        # Find PDF
        pdf_path = find_pdf_for_document(doc_id)

        if not pdf_path or not pdf_path.exists():
            print(f"  [SKIP] PDF not found")
            total_failed += len(provisions_list)
            continue

        print(f"  PDF: {pdf_path.name}")

        try:
            # Open PDF once for all provisions in this document
            doc = fitz.open(pdf_path)

            # Track which pages we've already extracted (avoid duplicates)
            extracted_pages = set()

            for prov in provisions_list:
                prov_id = prov['id']
                page_num = prov['page']

                if page_num > len(doc):
                    print(f"  [SKIP] Page {page_num} out of range")
                    total_failed += 1
                    continue

                # Skip if we already extracted this page for another provision
                page_key = f"{doc_id}_{page_num}"
                if page_key in extracted_pages:
                    # Just update database with same image path
                    image_url = f"/images/dcp/{doc_id}_page_{page_num}.png"
                    cur.execute(
                        "UPDATE regulatory_provisions SET pdf_page_image_url = %s WHERE id = %s",
                        (image_url, prov_id)
                    )
                    continue

                # Extract page as image
                page = doc[page_num - 1]  # 0-indexed

                # Render at 2x resolution for clarity
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                # Save image
                image_filename = f"{doc_id}_page_{page_num}.png"
                image_path = IMAGE_OUTPUT / image_filename
                pix.save(str(image_path))

                # Track size
                file_size = image_path.stat().st_size
                total_size_mb += file_size / (1024 * 1024)

                # Update database with image URL (relative to public/)
                image_url = f"/images/dcp/{image_filename}"
                cur.execute(
                    "UPDATE regulatory_provisions SET pdf_page_image_url = %s WHERE id = %s",
                    (image_url, prov_id)
                )

                extracted_pages.add(page_key)
                total_extracted += 1

                if total_extracted % 50 == 0:
                    print(f"  Extracted {total_extracted} pages so far...")

            doc.close()
            conn.commit()

            print(f"  [OK] Extracted {len(extracted_pages)} unique pages from this document")

        except Exception as e:
            print(f"  [ERROR] {e}")
            total_failed += len(provisions_list)

        print()

    cur.close()
    conn.close()

    # Summary
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total provisions processed: {len(provisions)}")
    print(f"Successfully extracted: {total_extracted} images")
    print(f"Failed: {total_failed}")
    print(f"Total image size: {total_size_mb:.1f} MB")
    print(f"Average per image: {(total_size_mb / total_extracted * 1024):.1f} KB")
    print()
    print(f"Images saved to: {IMAGE_OUTPUT}")
    print("=" * 70)


if __name__ == "__main__":
    print("=" * 70)
    print("EXTRACT ALL DCP PAGE IMAGES")
    print("=" * 70)
    print()

    # First, add column to database if it doesn't exist
    print("Step 1: Adding pdf_page_image_url column to database...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("""
            ALTER TABLE regulatory_provisions
            ADD COLUMN IF NOT EXISTS pdf_page_image_url TEXT;
        """)
        conn.commit()
        print("[OK] Column added/verified")
    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()

    cur.close()
    conn.close()

    print()
    print("Step 2: Extracting page images...")
    print()

    extract_all_page_images()
