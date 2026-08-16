#!/usr/bin/env python3
"""
Restore partial/broken tables using original MinerU JSON data

The MinerU _content_list.json files have the complete table structure.
We'll use those to replace the partial tables extracted by Camelot.
"""

import os
import sys
import json
import psycopg2
from pathlib import Path

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': 'localhost'
}

OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")


def find_mineru_json(pdf_filename):
    """Find the MinerU content_list.json for a PDF"""
    if not pdf_filename:
        return None

    doc_name = pdf_filename.replace('.pdf', '')

    # Look for MinerU output directory
    for json_path in OUTPUT_DIR.rglob("*_content_list.json"):
        dir_name = json_path.parent.parent.name
        if doc_name in dir_name or dir_name in doc_name:
            return json_path

    return None


def extract_table_from_json(json_path, page_num):
    """
    Extract table HTML from MinerU JSON for a specific page

    Returns: HTML table string or None
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # MinerU JSON structure: list of page objects
        # Each page has tables in various formats

        for page in data:
            if page.get('page_idx') == page_num - 1:  # 0-indexed
                # Look for tables in this page
                # Tables can be in different keys depending on MinerU version

                # Try different possible table locations
                tables = []

                if 'preproc_blocks' in page:
                    for block in page['preproc_blocks']:
                        if block.get('type') == 'table':
                            tables.append(block)

                if 'layout_dets' in page:
                    for det in page['layout_dets']:
                        if det.get('category_type') == 6:  # 6 = table in MinerU
                            tables.append(det)

                # Get the first/largest table
                if tables:
                    table = tables[0]

                    # Extract HTML if available
                    if 'html' in table:
                        return table['html']

                    # Or reconstruct from cells
                    if 'latex' in table:
                        # MinerU sometimes stores tables as LaTeX
                        # We'd need to convert, but for now skip
                        return None

        return None

    except Exception as e:
        print(f"  Error reading JSON: {e}")
        return None


def get_partial_tables():
    """Get list of partial tables (DS20.x pattern)"""
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
            AND provision_text LIKE '%Re-parsed%'
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


def update_provision_table(provision_id, new_html):
    """Update a provision with MinerU table HTML"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    marked_html = f"<!-- Restored from MinerU JSON -->\n{new_html}"

    update_query = """
        UPDATE regulatory_provisions
        SET provision_text = %s
        WHERE id = %s;
    """

    cur.execute(update_query, (marked_html, provision_id))
    conn.commit()

    cur.close()
    conn.close()


def main():
    print("=" * 70)
    print("Restore Tables from MinerU JSON")
    print("=" * 70)
    print()

    # Get partial tables
    print("Fetching partial tables...")
    partial_tables = get_partial_tables()

    print(f"Found {len(partial_tables)} partial tables")
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

    print(f"Across {len(tables_by_pdf)} unique PDF files")
    print()

    # Process each PDF
    total_fixed = 0
    total_failed = 0

    for pdf_filename, tables in tables_by_pdf.items():
        print(f"\n{'=' * 70}")
        print(f"PDF: {pdf_filename}")
        print(f"{'=' * 70}")
        print(f"Tables to restore: {len(tables)}")

        # Find MinerU JSON
        json_path = find_mineru_json(pdf_filename)

        if not json_path:
            print(f"[ERROR] Could not find MinerU JSON for: {pdf_filename}")
            total_failed += len(tables)
            continue

        print(f"[OK] Found JSON: {json_path}")
        print()

        # Process each table
        for table in tables:
            prov_id = table['id']
            page_num = table['page']

            print(f"Provision {prov_id} (page {page_num})...")

            # Extract from JSON
            table_html = extract_table_from_json(json_path, page_num)

            if not table_html:
                print(f"  [FAIL] No table found in JSON")
                total_failed += 1
                continue

            # Update database
            try:
                update_provision_table(prov_id, table_html)
                print(f"  [OK] Restored from MinerU JSON")
                total_fixed += 1
            except Exception as e:
                print(f"  [ERROR] Database update failed: {e}")
                total_failed += 1

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tables processed: {len(partial_tables)}")
    print(f"Successfully restored: {total_fixed}")
    print(f"Failed: {total_failed}")
    print()


if __name__ == "__main__":
    main()
