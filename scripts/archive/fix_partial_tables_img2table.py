#!/usr/bin/env python3
"""
Fix partial DS20.x tables using img2table borderless detection

These are 2-column Performance Criteria/Design Solutions tables that
Camelot couldn't extract properly. img2table is better at borderless tables.
"""

import os
import sys
import psycopg2
from pathlib import Path

sys.path.insert(0, 'scripts')
from reparse_table_structure import DB_CONFIG, find_pdf_file, copy_to_temp_path, update_provision_table

def extract_with_img2table(pdf_path, page_num):
    """Extract table using img2table with borderless detection"""
    try:
        from img2table.document import PDF
        from img2table.ocr import TesseractOCR

        # Copy to temp if path too long
        work_path = copy_to_temp_path(pdf_path) if len(str(pdf_path)) > 200 else pdf_path

        # Set up OCR
        ocr = TesseractOCR(
            lang="eng",
            tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )

        # Extract tables with borderless detection
        doc = PDF(src=str(work_path), pages=[page_num - 1])  # 0-indexed

        extracted_tables = doc.extract_tables(
            ocr=ocr,
            implicit_rows=True,
            borderless_tables=True,  # KEY: Enable borderless detection
            min_confidence=30  # Lower confidence for complex tables
        )

        if extracted_tables and len(extracted_tables) > 0:
            # Get first table on page
            table = extracted_tables[0]
            return table.html, "img2table"

        return None, None

    except Exception as e:
        print(f"  Error: {e}")
        return None, None


def get_partial_tables():
    """Get DS20.x partial tables"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = """
        SELECT
            id,
            document_id,
            pdf_page,
            pdf_source_file,
            ref_number
        FROM regulatory_provisions
        WHERE provision_text LIKE '%<table%'
            AND provision_text ~ 'DS[0-9]+\\.[0-9]+'
            AND pdf_source_file IS NOT NULL
            AND pdf_page IS NOT NULL
        ORDER BY document_id, pdf_page;
    """

    cur.execute(query)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def main():
    print("=" * 70)
    print("Fix Partial Tables with img2table")
    print("=" * 70)
    print()

    partial_tables = get_partial_tables()
    print(f"Found {len(partial_tables)} partial DS tables")
    print()

    # Group by PDF
    tables_by_pdf = {}
    for row in partial_tables:
        prov_id, doc_id, page_num, pdf_file, ref_num = row
        if pdf_file not in tables_by_pdf:
            tables_by_pdf[pdf_file] = []
        tables_by_pdf[pdf_file].append({
            'id': prov_id,
            'page': page_num,
            'ref': ref_num
        })

    total_fixed = 0
    total_failed = 0

    for pdf_filename, tables in tables_by_pdf.items():
        print(f"\n{'=' * 70}")
        print(f"PDF: {pdf_filename}")
        print(f"Tables: {len(tables)}")

        pdf_path = find_pdf_file(pdf_filename)
        if not pdf_path:
            print(f"[ERROR] PDF not found")
            total_failed += len(tables)
            continue

        print(f"[OK] Found: {pdf_path}")
        print()

        for table in tables:
            prov_id = table['id']
            page_num = table['page']

            print(f"Provision {prov_id} (page {page_num})...")

            # Extract with img2table
            new_html, parser = extract_with_img2table(pdf_path, page_num)

            if new_html:
                update_provision_table(prov_id, new_html, parser)
                print(f"  [OK] Fixed with img2table")
                total_fixed += 1
            else:
                print(f"  [FAIL] img2table failed")
                total_failed += 1

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total: {len(partial_tables)}")
    print(f"Fixed: {total_fixed}")
    print(f"Failed: {total_failed}")


if __name__ == "__main__":
    main()
