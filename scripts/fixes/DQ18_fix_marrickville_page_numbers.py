#!/usr/bin/env python3
"""DQ-18: Fix Marrickville pdf_page values by extracting from pdf_page_image_url.

The pdf_page field has relative page numbers (per split PDF file), but
pdf_page_image_url contains the correct absolute page number in the filename.

This script extracts the page number from the URL and updates pdf_page.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

# Use Supabase connection for production data
SUPABASE_DB = os.environ['DATABASE_URL']

def extract_page_from_url(url: str) -> int | None:
    """Extract page number from URL like '...page_5.png' -> 5"""
    if not url:
        return None
    match = re.search(r'page_(\d+)\.', url)
    return int(match.group(1)) if match else None

def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18: FIX MARRICKVILLE PDF PAGE NUMBERS')
    print('=' * 60)

    # Step 1: Get current state - count mismatches
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    """)
    total = cur.fetchone()[0]
    print(f'\nTotal Marrickville provisions with URLs: {total}')

    # Get all provisions with their current pdf_page and URL
    cur.execute("""
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    """)
    rows = cur.fetchall()

    # Analyze mismatches
    mismatches = []
    for row_id, current_page, url in rows:
        url_page = extract_page_from_url(url)
        if url_page is not None and current_page != url_page:
            mismatches.append((row_id, current_page, url_page, url))

    print(f'Provisions with page mismatch: {len(mismatches)}')

    if not mismatches:
        print('\nNo mismatches found! Database is already correct.')
        conn.close()
        return

    # Show sample of mismatches
    print('\nSample mismatches (first 10):')
    for row_id, current, correct, url in mismatches[:10]:
        print(f'  ID {row_id}: pdf_page={current} -> {correct} (from {url[-40:]})')

    # Step 2: Fix the mismatches
    print(f'\nFixing {len(mismatches)} mismatches...')

    fixed = 0
    for row_id, current_page, correct_page, url in mismatches:
        cur.execute("""
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        """, (correct_page, row_id))
        fixed += cur.rowcount

    conn.commit()
    print(f'Fixed {fixed} provisions')

    # Step 3: Verify
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions rp
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
          AND pdf_page != CAST(
            SUBSTRING(pdf_page_image_url FROM 'page_([0-9]+)\.') AS INTEGER
          )
    """)
    remaining = cur.fetchone()[0]

    if remaining == 0:
        print('\n✓ All Marrickville page numbers now match URLs!')
    else:
        print(f'\nWARNING: {remaining} provisions still have mismatches')

    conn.close()
    print('\nDone!')

if __name__ == '__main__':
    main()
