#!/usr/bin/env python3
"""
Fix ALL broken tables in database using pdfplumber

This script:
1. Finds all provisions with broken/incomplete tables
2. Re-extracts them from PDFs using pdfplumber
3. Updates database with corrected HTML tables

pdfplumber is the ONLY tool that works reliably for complex DCP tables.
"""
import pdfplumber
import psycopg2
from pathlib import Path
from collections import defaultdict
import sys

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")


def find_pdf_path(pdf_filename: str) -> Path:
    """Find the original PDF file in output directory"""
    # Search for _origin.pdf files
    for pdf_path in OUTPUT_DIR.rglob("*_origin.pdf"):
        if pdf_filename.replace('.pdf', '') in pdf_path.parent.parent.name:
            return pdf_path
    return None


def get_broken_tables():
    """Get all provisions with broken tables"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = """
        SELECT
            id,
            document_id,
            pdf_source_file,
            pdf_page,
            ref_number
        FROM regulatory_provisions
        WHERE provision_text LIKE '%<table%'
            AND pdf_source_file IS NOT NULL
            AND pdf_page IS NOT NULL
            AND (
                provision_text NOT LIKE '%</table>%'
                OR provision_text ~ '</td><td>[a-z]'
                OR provision_text LIKE '%<td></td><td></td><td></td>%'
                OR (LENGTH(provision_text) < 500 AND provision_text LIKE '%<table%')
            )
        ORDER BY pdf_source_file, pdf_page;
    """

    cur.execute(query)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def extract_table_from_pdf(pdf_path: Path, page_num: int):
    """Extract table from PDF page using pdfplumber"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num > len(pdf.pages):
                return None

            page = pdf.pages[page_num - 1]  # 0-indexed
            tables = page.extract_tables()

            if not tables:
                return None

            # Get largest table (main content)
            table = max(tables, key=lambda t: len(t) * len(t[0]) if t and t[0] else 0)

            return table

    except Exception as e:
        print(f"    [ERROR] pdfplumber failed: {e}")
        return None


def table_to_html(rows):
    """Convert table rows to HTML"""
    if not rows or len(rows) < 1:
        return ""

    html = "<table>\n"

    # Detect if first row is header (short text, all caps, or contains keywords)
    first_row = rows[0]
    is_header = any(
        cell and (
            len(cell) < 50 or
            cell.isupper() or
            any(kw in cell.lower() for kw in ['requirement', 'category', 'type', 'use', 'criteria', 'solution'])
        )
        for cell in first_row if cell
    )

    if is_header:
        html += "<thead><tr>\n"
        for cell in first_row:
            html += f"  <th>{(cell or '').strip()}</th>\n"
        html += "</tr></thead>\n<tbody>\n"
        data_rows = rows[1:]
    else:
        html += "<tbody>\n"
        data_rows = rows

    # Add data rows
    for row in data_rows:
        html += "<tr>\n"
        for cell in row:
            html += f"  <td>{(cell or '').strip()}</td>\n"
        html += "</tr>\n"

    html += "</tbody>\n</table>"

    return html


def update_provision(prov_id: int, html_table: str):
    """Update provision with corrected table"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(
        "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
        (html_table, prov_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def main():
    print("=" * 70)
    print("Fixing ALL Broken Tables with PDFPlumber")
    print("=" * 70)
    print()

    # Get all broken tables
    print("[1/4] Finding broken tables...")
    broken_tables = get_broken_tables()

    print(f"[OK] Found {len(broken_tables)} broken tables")
    print()

    # Group by PDF to minimize file I/O
    print("[2/4] Grouping by PDF...")
    tables_by_pdf = defaultdict(list)

    for prov_id, doc_id, pdf_file, page_num, ref_num in broken_tables:
        tables_by_pdf[pdf_file].append({
            'id': prov_id,
            'page': page_num,
            'ref': ref_num,
            'doc_id': doc_id
        })

    print(f"[OK] Grouped into {len(tables_by_pdf)} PDF files")
    print()

    # Process each PDF
    print("[3/4] Re-extracting tables...")
    print()

    total_fixed = 0
    total_failed = 0
    pdf_count = 0

    for pdf_filename, tables in tables_by_pdf.items():
        pdf_count += 1
        print(f"[{pdf_count}/{len(tables_by_pdf)}] {pdf_filename}")
        print(f"  Tables to fix: {len(tables)}")

        # Find PDF file
        pdf_path = find_pdf_path(pdf_filename)

        if not pdf_path:
            print(f"  [ERROR] PDF not found: {pdf_filename}")
            total_failed += len(tables)
            continue

        print(f"  [OK] Found: {pdf_path.name}")

        # Extract each table
        for table_info in tables:
            prov_id = table_info['id']
            page_num = table_info['page']

            # Extract table
            table_data = extract_table_from_pdf(pdf_path, page_num)

            if not table_data:
                print(f"    [FAIL] Provision {prov_id} (page {page_num}) - no table found")
                total_failed += 1
                continue

            # Convert to HTML
            html = table_to_html(table_data)

            if not html or len(html) < 50:
                print(f"    [FAIL] Provision {prov_id} (page {page_num}) - empty table")
                total_failed += 1
                continue

            # Update database
            try:
                update_provision(prov_id, html)
                total_fixed += 1

                if total_fixed % 100 == 0:
                    print(f"    [OK] Fixed {total_fixed} tables so far...")

            except Exception as e:
                print(f"    [ERROR] Provision {prov_id} - database update failed: {e}")
                total_failed += 1

        print()

    # Summary
    print()
    print("=" * 70)
    print("[4/4] SUMMARY")
    print("=" * 70)
    print(f"Total broken tables found: {len(broken_tables)}")
    print(f"Successfully fixed: {total_fixed}")
    print(f"Failed: {total_failed}")
    print(f"Success rate: {100 * total_fixed / len(broken_tables):.1f}%")
    print()

    if total_fixed > 0:
        print("[OK] Table re-extraction complete!")
        print()
        print("Verify in database:")
        print('  psql -U postgres -h localhost -d nsw_planning -c ')
        print('    "SELECT COUNT(*) FROM regulatory_provisions ')
        print("     WHERE provision_text LIKE '%<table%' ")
        print("       AND provision_text LIKE '%</table>%';\"")


if __name__ == "__main__":
    main()
