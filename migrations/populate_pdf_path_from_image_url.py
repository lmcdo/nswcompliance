#!/usr/bin/env python3
"""
Populate pdf_path column from pdf_page_image_url
This should have been set during extraction but wasn't for some reason.

Pattern: /pdf-pages/marr_Marrickville_DCP_2011_-_2_1_Urban_Design_page_10.png
         → Marrickville DCP 2011 - Part 2
"""

import psycopg2
import os
import re
from dotenv import load_dotenv

load_dotenv()

def derive_pdf_path(pdf_page_image_url):
    """Extract pdf_path from PNG filename - handles Marrickville, Ashfield, and Leichhardt patterns"""
    if not pdf_page_image_url:
        return None

    # Pattern 1: Marrickville with section names
    # Examples:
    #   /pdf-pages/marr_Marrickville_DCP_2011_-_2_1_Urban_Design_page_10.png
    #   /pdf-pages/marr_Marrickville_DCP_2011_-_4.1_Low_Density_Residentia_page_10.png
    #   /pdf-pages/marr_Marrickville_DCP_2011_-_8.0_Heritage_page_100.png
    #   /pdf-pages/marr_Marrickville_DCP_2011_-_8.0_Heritage_-_Part1_(page_page_55.png
    match = re.search(r'/pdf-pages/marr_(.+)_page_\d+\.png$', pdf_page_image_url)
    if match:
        doc_name = match.group(1).replace('_', ' ')

        # Extract part number - handles both "2 1" (space) and "4.1" (decimal) and "8.0" (decimal)
        # Match: "Marrickville DCP 2011 - 2 1 Urban" or "Marrickville DCP 2011 - 4.1 Low" or "Marrickville DCP 2011 - 8.0 Heritage"
        part_match = re.search(r'^(.*?)\s+-\s+(\d+(?:[.\s]\d+)?)', doc_name)
        if part_match:
            base_name = part_match.group(1)  # "Marrickville DCP 2011"
            part_spec = part_match.group(2)  # "2 1" or "4.1" or "8.0"

            # Normalize to "Part X" format
            # "2 1" -> "Part 2"
            # "4.1" -> "Part 4"
            # "8.0" -> "Part 8"
            # "7.3" -> "Part 7"
            part_number = part_spec.split()[0] if ' ' in part_spec else part_spec.split('.')[0]
            return f"{base_name} - Part {part_number}"

    # Pattern 2: Ashfield Chapter F
    # /pdf-pages/ashfield_chapter_f_page_15.png
    # /pdf-pages/ashf_Inner_West_Ashfield_DCP_2016_-_Chapter_F_-_Development_Category_page_5.png
    if '/ashfield_chapter_f_page' in pdf_page_image_url or '/ashf_Inner_West_Ashfield' in pdf_page_image_url:
        return "Ashfield DCP 2016 - Chapter F"

    # Pattern 3: Leichhardt Parts
    # /pdf-pages/leichhardt-part-b/page_3.png
    # /pdf-pages/leichhardt-part-e/page_13.png
    match = re.search(r'/pdf-pages/leichhardt-part-([a-z](?:\.\d)?)/page_\d+\.png$', pdf_page_image_url, re.IGNORECASE)
    if match:
        part = match.group(1).upper()
        return f"Leichhardt DCP 2013 - Part {part}"

    return None


def main():
    conn = psycopg2.connect(os.getenv('DIRECT_URL'))
    cur = conn.cursor()

    # Get all records with pdf_page_image_url but no pdf_path
    cur.execute("""
        SELECT id, pdf_page_image_url
        FROM dcp_general_requirements
        WHERE pdf_page_image_url IS NOT NULL
        AND (pdf_path IS NULL OR pdf_path = '')
    """)

    rows = cur.fetchall()
    print(f"Found {len(rows)} records missing pdf_path")

    updated = 0
    failed = 0

    for row_id, image_url in rows:
        pdf_path = derive_pdf_path(image_url)

        if pdf_path:
            cur.execute("""
                UPDATE dcp_general_requirements
                SET pdf_path = %s
                WHERE id = %s
            """, (pdf_path, row_id))
            updated += 1

            if updated <= 5:  # Show first 5 examples
                print(f"[OK] ID {row_id}: {image_url} -> {pdf_path}")
        else:
            failed += 1
            print(f"[FAIL] ID {row_id}: Could not derive from {image_url}")

    conn.commit()

    print(f"\n{'='*60}")
    print(f"Updated: {updated}")
    print(f"Failed:  {failed}")
    print(f"{'='*60}")

    # Verify
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(pdf_path) as with_path,
            COUNT(*) - COUNT(pdf_path) as missing_path
        FROM dcp_general_requirements
    """)

    result = cur.fetchone()
    print(f"\nFinal state:")
    print(f"  Total records: {result[0]}")
    print(f"  With pdf_path: {result[1]}")
    print(f"  Missing:       {result[2]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
