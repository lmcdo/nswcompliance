#!/usr/bin/env python3
"""
Re-parse the 56 Tesseract-OCRed tables to restore table structure

These tables had their text fixed by Tesseract, but lost their HTML structure.
Now we'll re-extract them with Camelot/img2table to get proper table HTML.
"""

import os
import sys
import psycopg2
from pathlib import Path

# Import from reparse_table_structure
sys.path.insert(0, 'scripts')
from reparse_table_structure import (
    find_pdf_file, reparse_table, update_provision_table, DB_CONFIG
)


def get_tesseract_tables():
    """Get list of tables that were re-OCRed with Tesseract"""
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
        WHERE provision_text LIKE '%Re-OCRed with Tesseract%'
            AND ref_number LIKE '%table_in_%'
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
    print("Fix Tesseract-OCRed Tables - Restore Table Structure")
    print("=" * 70)
    print()

    # Get Tesseract-OCRed tables
    print("Fetching Tesseract-OCRed tables...")
    tesseract_tables = get_tesseract_tables()

    print(f"Found {len(tesseract_tables)} tables to re-parse")
    print()

    # Group by PDF
    tables_by_pdf = {}
    for row in tesseract_tables:
        prov_id, doc_id, page_num, pdf_file, ref_num = row

        if pdf_file not in tables_by_pdf:
            tables_by_pdf[pdf_file] = []

        tables_by_pdf[pdf_file].append({
            'id': prov_id,
            'page': page_num,
            'ref': ref_num
        })

    print(f"Across {len(tables_by_pdf)} unique PDF files")
    print()

    # Process each PDF
    total_fixed = 0
    total_failed = 0

    for pdf_filename, tables in tables_by_pdf.items():
        print(f"\n{'=' * 70}")
        print(f"PDF: {pdf_filename}")
        print(f"{'=' * 70}")
        print(f"Tables to re-parse: {len(tables)}")

        # Find PDF file
        pdf_path = find_pdf_file(pdf_filename)

        if not pdf_path:
            print(f"[ERROR] Could not find PDF file: {pdf_filename}")
            total_failed += len(tables)
            continue

        print(f"[OK] Found: {pdf_path}")
        print()

        # Process each table
        for table in tables:
            prov_id = table['id']
            page_num = table['page']

            print(f"Provision {prov_id} (page {page_num})...")

            # Re-parse table
            new_html, parser_used = reparse_table(pdf_path, page_num)

            if not new_html:
                print(f"  [FAIL] All parsers failed")
                total_failed += 1
                continue

            # Update database
            try:
                update_provision_table(prov_id, new_html, parser_used)
                print(f"  [OK] Updated with {parser_used}")
                total_fixed += 1
            except Exception as e:
                print(f"  [ERROR] Database update failed: {e}")
                total_failed += 1

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tables processed: {len(tesseract_tables)}")
    print(f"Successfully re-parsed: {total_fixed}")
    print(f"Failed: {total_failed}")
    print()

    if total_fixed > 0:
        print("[OK] Table structure restoration complete!")


if __name__ == "__main__":
    main()
