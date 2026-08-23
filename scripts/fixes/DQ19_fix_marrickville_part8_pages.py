#!/usr/bin/env python3
"""DQ-19 FIX: Marrickville Part 8 Heritage pdf_page values.

Issue: pdf_page values are raw url_page numbers, not relative page within section.
- url_page 15 = "8.1 Introduction" (first page of Part 8 content) = should be pdf_page 1
- url_page 23 = page 9 in PDF footer

Fix: pdf_page = url_page - 14

Applies to provisions with pdf_page_image_url containing '8.0_Heritage' or '8_Heritage'.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

# Content starts at url_page 15 (which is page 1 in PDF footer)
CONTENT_START_URL = 15
OFFSET = CONTENT_START_URL - 1  # 14


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 70)
    print('DQ-19 FIX: MARRICKVILLE PART 8 HERITAGE PAGE NUMBERS')
    print(f'Offset: url_page - {OFFSET} = pdf_page')
    print('=' * 70)

    # Get all Marrickville Part 8 Heritage provisions
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage%'
           OR pdf_page_image_url LIKE '%8_Heritage%'
           OR (document_id ILIKE '%Marrickville%Part%8%' AND pdf_page_image_url IS NOT NULL)
    ''')
    rows = cur.fetchall()

    print(f'\nFound {len(rows)} Marrickville Part 8 Heritage provisions')

    # Calculate fixes
    fixes = []
    for row_id, pdf_page, url in rows:
        # Extract url_page from URL
        match = re.search(r'page_(\d+)\.', url)
        if not match:
            continue
        url_page = int(match.group(1))

        # Calculate correct pdf_page
        correct_pdf_page = url_page - OFFSET
        if correct_pdf_page < 1:
            correct_pdf_page = 1  # Don't go below 1

        if pdf_page != correct_pdf_page:
            fixes.append((row_id, pdf_page, correct_pdf_page, url_page))

    print(f'Provisions needing fix: {len(fixes)}')

    if not fixes:
        print('\nNo fixes needed!')
        conn.close()
        return

    # Show samples
    print('\nSample fixes:')
    for row_id, old, new, url_page in fixes[:10]:
        print(f'  ID {row_id}: url_page={url_page}, pdf_page {old} -> {new}')

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

    # Verify
    print('\n=== Verification ===')
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 60) as text
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage%page_15%'
           OR pdf_page_image_url LIKE '%8_Heritage%page_15%'
        LIMIT 3
    ''')
    results = cur.fetchall()
    print('url_page 15 (should be pdf_page 1):')
    for row_id, pdf_page, url, text in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}, text: {text}...')

    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%8.0_Heritage%page_23%'
           OR pdf_page_image_url LIKE '%8_Heritage%page_23%'
        LIMIT 3
    ''')
    results = cur.fetchall()
    print('\nurl_page 23 (should be pdf_page 9):')
    for row_id, pdf_page, url in results:
        print(f'  ID {row_id}: pdf_page={pdf_page}')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
