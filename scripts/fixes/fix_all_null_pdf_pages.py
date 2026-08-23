#!/usr/bin/env python3
"""Fix all NULL pdf_page values by extracting from pdf_page_image_url.

This uses the SAME logic that was working before the Jan 28 restore.

The pdf_page_image_url contains the correct page number in the filename (page_X.png).
This script extracts X and populates pdf_page for all provisions where it's NULL.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

# Use Supabase connection
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

    print('=' * 70)
    print('FIX ALL NULL PDF_PAGE VALUES FROM IMAGE URLs')
    print('=' * 70)
    print('This restores the logic that was working before Jan 28 restore')
    print()

    # Step 1: Get current state
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE pdf_page IS NULL
          AND pdf_page_image_url IS NOT NULL
    """)
    null_count = cur.fetchone()[0]
    print(f'Provisions with NULL pdf_page but has URL: {null_count:,}')

    if null_count == 0:
        print('\nNo NULL pages to fix! Database is already correct.')
        conn.close()
        return

    # Step 2: Get breakdown by council
    cur.execute("""
        SELECT
            CASE
                WHEN document_id LIKE '%Leichhardt%' THEN 'Leichhardt'
                WHEN document_id LIKE '%Marrickville%' THEN 'Marrickville'
                WHEN document_id LIKE '%Ashfield%' THEN 'Ashfield'
                ELSE 'Other'
            END as council,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE pdf_page IS NULL
          AND pdf_page_image_url IS NOT NULL
        GROUP BY council
        ORDER BY count DESC
    """)

    print('\nBreakdown by council:')
    for council, count in cur.fetchall():
        print(f'  {council}: {count:,}')

    # Step 3: Get all provisions with NULL pdf_page and extract from URL
    cur.execute("""
        SELECT id, pdf_page_image_url, document_id
        FROM regulatory_provisions
        WHERE pdf_page IS NULL
          AND pdf_page_image_url IS NOT NULL
        ORDER BY id
    """)
    rows = cur.fetchall()

    print(f'\nProcessing {len(rows):,} provisions...')

    # Extract page numbers
    to_update = []
    failed = []
    for row_id, url, doc_id in rows:
        page_num = extract_page_from_url(url)
        if page_num is not None:
            to_update.append((page_num, row_id))
        else:
            failed.append((row_id, url, doc_id))

    print(f'  Can extract page: {len(to_update):,}')
    print(f'  Failed to extract: {len(failed):,}')

    if failed:
        print('\nSample failures (first 5):')
        for row_id, url, doc_id in failed[:5]:
            print(f'  ID {row_id}: {doc_id[:40]} - {url[-50:]}')

    if not to_update:
        print('\nERROR: Could not extract any page numbers from URLs!')
        conn.close()
        return

    # Step 4: Update database
    print(f'\nUpdating {len(to_update):,} provisions...')

    updated = 0
    for page_num, row_id in to_update:
        cur.execute("""
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        """, (page_num, row_id))
        updated += cur.rowcount

    conn.commit()
    print(f'✓ Updated {updated:,} provisions')

    # Step 5: Verify results
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE pdf_page IS NULL
          AND pdf_page_image_url IS NOT NULL
    """)
    remaining = cur.fetchone()[0]

    print('\n' + '=' * 70)
    print('RESULTS')
    print('=' * 70)
    print(f'Before: {null_count:,} NULL pdf_page')
    print(f'After:  {remaining:,} NULL pdf_page')
    print(f'Fixed:  {null_count - remaining:,} provisions')

    if remaining == 0:
        print('\n✅ SUCCESS! All provisions with URLs now have pdf_page populated')
    else:
        print(f'\n⚠️  {remaining:,} provisions still have NULL pdf_page')
        print('   (These may not have pdf_page_image_url)')

    # Check overall coverage
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(pdf_page) as has_page,
            ROUND(COUNT(pdf_page) * 100.0 / COUNT(*), 1) as pct
        FROM regulatory_provisions
    """)
    total, has_page, pct = cur.fetchone()

    print(f'\nOverall pdf_page coverage: {has_page:,} / {total:,} ({pct}%)')

    conn.close()
    print('\nDone!')

if __name__ == '__main__':
    main()
