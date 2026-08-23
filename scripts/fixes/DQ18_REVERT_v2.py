#!/usr/bin/env python3
"""DQ-18 REVERT v2: Fix ALL Marrickville pdf_page values.

The previous fix set pdf_page = url_page, but:
- URL page numbers are EXTRACTION SEQUENCE numbers
- pdf_page should be ACTUAL DCP PAGE NUMBER

This version extracts the Part number from URL and applies the correct offset.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

def extract_page_from_url(url: str) -> int | None:
    """Extract page number from URL like '...page_5.png' -> 5"""
    if not url:
        return None
    match = re.search(r'page_(\d+)\.', url)
    return int(match.group(1)) if match else None

def get_offset_for_url(url: str) -> int:
    """Get offset based on URL section pattern."""
    if not url:
        return 4  # Default offset

    # Special Heritage cases (check these first - more specific)
    if '_8.0_Heritage_-_Part1_' in url or '_8.0_Heritage_-_Part1(' in url:
        return 14
    if '_8.0_Heritage_-_Part2_' in url or '_8.0_Heritage_-_Part2(' in url:
        return -48  # Adds 48
    if '_8.0_Heritage_-_Part4_' in url or '_8.0_Heritage_-_Part4(' in url:
        return 7
    if '_8.0_Heritage' in url:
        return -48  # Default heritage adds 48

    # Part 4.1 Low Density - offset 6
    if '_4.1_Low_Density' in url or '_4_1_Low_Density' in url:
        return 6

    # Part 7.1 childcare - offset 6
    if '_7_1_childcare' in url or '_7.1_childcare' in url:
        return 6

    # Most other sections use offset 4
    # This includes: Part 1, Part 2.x, Part 3, Part 4.2+, Part 5, Part 6, Part 7.3, Part 9
    return 4

def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 REVERT v2: Fix ALL Marrickville pdf_page values')
    print('=' * 60)

    # Get all Marrickville provisions with URLs
    cur.execute("""
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f'\nTotal Marrickville provisions with URLs: {len(rows)}')

    # Calculate fixes
    fixes = []
    for row_id, current_page, url in rows:
        url_page = extract_page_from_url(url)
        if url_page is None or current_page is None:
            continue

        offset = get_offset_for_url(url)
        correct_page = url_page - offset

        # Only fix if page would be positive and different
        if correct_page > 0 and correct_page != current_page:
            fixes.append((row_id, current_page, correct_page, url, offset))

    print(f'Provisions to fix: {len(fixes)}')

    if not fixes:
        print('\nNo fixes needed.')
        conn.close()
        return

    # Show samples by offset
    print('\nSample fixes by offset:')
    offsets_shown = {}
    for row_id, current, correct, url, offset in fixes[:100]:
        if offset not in offsets_shown:
            offsets_shown[offset] = 0
        if offsets_shown[offset] < 3:
            offsets_shown[offset] += 1
            section = url.split('/')[-1][:40] if url else '?'
            print(f'  offset={offset}: pdf_page {current} -> {correct} | {section}')

    # Apply fixes
    print(f'\nApplying {len(fixes)} fixes...')
    fixed = 0
    for row_id, current_page, correct_page, url, offset in fixes:
        cur.execute("""
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        """, (correct_page, row_id))
        fixed += cur.rowcount

    conn.commit()
    print(f'Fixed {fixed} provisions')

    # Verify
    print('\nVerification - checking page_5 URLs:')
    cur.execute("""
        SELECT pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url LIKE '%page_5.%'
        LIMIT 10
    """)
    for row in cur.fetchall():
        section = row[1].split('/')[-1][:40] if row[1] else '?'
        print(f'  pdf_page={row[0]} | {section}')

    conn.close()
    print('\nDone!')

if __name__ == '__main__':
    main()
