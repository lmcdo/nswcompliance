#!/usr/bin/env python3
"""
Manually fix the two main Ashfield parking tables using pdfplumber
These tables have complex structure that Camelot can't handle properly
"""
import pdfplumber
import psycopg2
from pathlib import Path

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

PDF_PATH = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output\Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments\auto\Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments_origin.pdf")

# Table specifications
TABLES = [
    {
        'id': 58309,
        'pages': [64, 65],  # Spans 2 pages
        'name': 'Market/Motor showroom/Plant Nursery/Food & Drink/Retail/Service Stations'
    },
    {
        'id': 58312,
        'pages': [66, 67],  # Spans 2 pages
        'name': 'Place of Worship/Schools/Professional Consulting/Public Buildings/Tertiary Education'
    }
]


def extract_multipage_table(pdf_path, page_numbers):
    """Extract table that spans multiple pages using pdfplumber"""
    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num in page_numbers:
            page = pdf.pages[page_num - 1]  # 0-indexed

            # Extract tables from page
            tables = page.extract_tables()

            if not tables:
                print(f"    [WARN] No tables on page {page_num}")
                continue

            # Use the largest table (main content)
            table = max(tables, key=lambda t: len(t) * len(t[0]) if t and t[0] else 0)

            print(f"    [OK] Page {page_num}: Found table with {len(table)} rows")

            # Add rows (skip header if not first page)
            if page_num == page_numbers[0]:
                all_rows.extend(table)
            else:
                # Skip header row on continuation pages
                all_rows.extend(table[1:] if len(table) > 1 else table)

    return all_rows


def table_to_html(rows):
    """Convert table rows to HTML with proper headers"""
    if not rows or len(rows) < 2:
        return ""

    html = "<table>\n"

    # First row is header
    html += "<thead><tr>\n"
    for cell in rows[0]:
        cell_text = (cell or "").strip()
        html += f"  <th>{cell_text}</th>\n"
    html += "</tr></thead>\n"

    # Remaining rows are data
    html += "<tbody>\n"
    for row in rows[1:]:
        html += "<tr>\n"
        for cell in row:
            cell_text = (cell or "").strip()
            html += f"  <td>{cell_text}</td>\n"
        html += "</tr>\n"
    html += "</tbody>\n"

    html += "</table>"

    return html


def main():
    if not PDF_PATH.exists():
        print(f"[ERROR] PDF not found: {PDF_PATH}")
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 70)
    print("Fixing Ashfield Parking Tables with PDFPlumber")
    print("=" * 70)
    print()

    for table_info in TABLES:
        print(f"\n[EXTRACTING] {table_info['name']}")
        print(f"  Provision ID: {table_info['id']}")
        print(f"  Pages: {table_info['pages']}")

        # Extract full table across pages
        rows = extract_multipage_table(PDF_PATH, table_info['pages'])

        if not rows:
            print(f"  [ERROR] No data extracted")
            continue

        print(f"  [OK] Extracted {len(rows)} rows total")

        # Convert to HTML
        html = table_to_html(rows)

        if not html:
            print(f"  [ERROR] Could not convert to HTML")
            continue

        print(f"  [OK] Generated HTML ({len(html)} chars)")

        # Update database
        cur.execute(
            "UPDATE regulatory_provisions SET provision_text = %s WHERE id = %s",
            (html, table_info['id'])
        )

        print(f"  [OK] Updated provision {table_info['id']}")

    conn.commit()
    cur.close()
    conn.close()

    print("\n" + "=" * 70)
    print("[DONE] Ashfield parking tables fixed")
    print("=" * 70)


if __name__ == "__main__":
    main()
