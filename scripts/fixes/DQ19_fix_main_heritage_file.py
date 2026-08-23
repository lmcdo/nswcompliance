#!/usr/bin/env python3
"""DQ-19 FIX: Main Marrickville Heritage file page numbers.

The main file 'marr_Marrickville_DCP_2011_-_8.0_Heritage' also has:
- url_page 15 = "8.1 Introduction" = PDF footer shows "Page 1"

Same fix as the Part file: pdf_page = url_page - 14 for content pages.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

# Content page 1 = url_page 15
CONTENT_START_URL = 15
OFFSET = CONTENT_START_URL - 1  # 14


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 70)
    print('DQ-19 FIX: MAIN MARRICKVILLE HERITAGE FILE PAGE NUMBERS')
    print(f'Content starts at url_page {CONTENT_START_URL} = pdf_page 1')
    print(f'Formula: pdf_page = url_page - {OFFSET}')
    print('=' * 70)

    # Get provisions from the main file (not Part1/2/3/4 or -Part)
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
    ''')
    rows = cur.fetchall()

    print(f'\nFound {len(rows)} provisions in main Heritage file')

    # Calculate fixes
    fixes = []
    for row_id, pdf_page, url in rows:
        match = re.search(r'page_(\d+)\.', url)
        if not match:
            continue
        url_page = int(match.group(1))

        # For pages before content start, set to 1 (TOC/front matter)
        if url_page < CONTENT_START_URL:
            correct_pdf_page = 1
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
        print(f'  ID {row_id}: url_page={url_page:3d}, pdf_page {old:3d} -> {new:3d}')

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
        WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_15.%'
    ''')
    results = cur.fetchall()
    print(f'url_page 15 (should be pdf_page 1 - "8.1 Introduction"):')
    for row_id, pdf_page, text in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}, text: {text}...')

    # url_page 154 (Dulwich Hill HCA) - should be 154 - 14 = 140
    cur.execute('''
        SELECT id, pdf_page, LEFT(provision_text, 60) as text
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_154.%'
    ''')
    results = cur.fetchall()
    print(f'\nurl_page 154 (should be pdf_page 140):')
    for row_id, pdf_page, text in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}, text: {text}...')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
