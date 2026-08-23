#!/usr/bin/env python3
"""DQ-19 FIX v3: Marrickville Part 8 Heritage - specific fix for the Part subgroup.

The PDF file '8.0_Heritage_-_Part_page_N.png' has:
- url_page 15 = "8.1 Introduction" = PDF footer shows "Page 1"
- User confirmed: url_page 23 should be pdf_page 9 (23 - 15 + 1 = 9) ✓

So for this specific file: pdf_page = url_page - 14 (content starts at url 15)
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

# For 8.0_Heritage_-_Part, content page 1 = url_page 15
CONTENT_START_URL = 15
OFFSET = CONTENT_START_URL - 1  # 14


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 70)
    print('DQ-19 FIX v3: MARRICKVILLE 8.0_Heritage_-_Part PAGE NUMBERS')
    print(f'Content starts at url_page {CONTENT_START_URL} = pdf_page 1')
    print(f'Formula: pdf_page = url_page - {OFFSET}')
    print('=' * 70)

    # Only fix the specific file pattern that has the wrong offset
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage_-_Part_page_%'
          AND pdf_page_image_url NOT LIKE '%Part1%'
          AND pdf_page_image_url NOT LIKE '%Part2%'
          AND pdf_page_image_url NOT LIKE '%Part3%'
          AND pdf_page_image_url NOT LIKE '%Part4%'
    ''')
    rows = cur.fetchall()

    print(f'\nFound {len(rows)} provisions in 8.0_Heritage_-_Part (not Part1/2/3/4)')

    # Calculate fixes
    fixes = []
    for row_id, pdf_page, url in rows:
        match = re.search(r'page_(\d+)\.', url)
        if not match:
            continue
        url_page = int(match.group(1))

        # For pages before content start, set to 1 (TOC pages)
        if url_page < CONTENT_START_URL:
            correct_pdf_page = 1  # Or we could skip these
        else:
            correct_pdf_page = url_page - OFFSET

        if pdf_page != correct_pdf_page:
            fixes.append((row_id, pdf_page, correct_pdf_page, url_page))

    print(f'Provisions needing fix: {len(fixes)}')

    if not fixes:
        print('\nNo fixes needed!')
        conn.close()
        return

    # Show samples
    print('\nSample fixes:')
    for row_id, old, new, url_page in fixes[:15]:
        print(f'  ID {row_id}: url_page={url_page:2d}, pdf_page {old:2d} -> {new:2d}')

    # Apply fixes
    print(f'\nApplying {len(fixes)} fixes...')
    for row_id, old, new, url_page in fixes:
        cur.execute('''
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        ''', (new, row_id))

    conn.commit()
    print(f'Fixed {len(fixes)} provisions')

    # Verify key pages
    print('\n=== Verification ===')

    # url_page 15 should be pdf_page 1
    cur.execute('''
        SELECT id, pdf_page, LEFT(provision_text, 60) as text
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage_-_Part_page_15.%'
    ''')
    results = cur.fetchall()
    print(f'url_page 15 (should be pdf_page 1 - "8.1 Introduction"):')
    for row_id, pdf_page, text in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}, text: {text}...')

    # url_page 23 should be pdf_page 9
    cur.execute('''
        SELECT id, pdf_page
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage_-_Part_page_23.%'
    ''')
    results = cur.fetchall()
    print(f'\nurl_page 23 (should be pdf_page 9):')
    for row_id, pdf_page in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
