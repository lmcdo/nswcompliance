#!/usr/bin/env python3
"""DQ-18 FIX: Direct fix for Part 4.1 based on confirmed data.

User confirmed: page_7.png shows PDF footer "1" (first page of Part 4.1)
Therefore: min_url for Part 4.1 content = 7

Pages 3-6 are TOC/intro pages, not the actual Part 4.1 content start.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 FIX: PART 4.1 DIRECT FIX')
    print('=' * 60)

    # Get Part 4.1 provisions (URL contains _4.1_)
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%_4.1_%'
    ''')
    rows = cur.fetchall()
    print(f'\nPart 4.1 provisions: {len(rows)}')

    # User confirmed: page_7.png = PDF page 1
    # So min_content_url = 7
    MIN_CONTENT_URL = 7

    fixes = []
    for row_id, current_pdf_page, url in rows:
        match = re.search(r'page_(\d+)\.', url)
        if not match:
            continue
        url_page = int(match.group(1))

        # Calculate correct pdf_page
        # For pages before the content start (3-6), set to 1 (intro/TOC)
        if url_page < MIN_CONTENT_URL:
            correct_page = 1  # TOC/intro pages
        else:
            correct_page = url_page - MIN_CONTENT_URL + 1

        if current_pdf_page != correct_page:
            fixes.append((row_id, correct_page, current_pdf_page, url_page))

    print(f'Fixes needed: {len(fixes)}')

    if fixes:
        print('\nSample fixes:')
        for row_id, new, old, url_page in fixes[:10]:
            print(f'  ID {row_id}: url_page={url_page}, pdf_page {old} -> {new}')

        print(f'\nApplying {len(fixes)} fixes...')
        for row_id, correct_page, _, _ in fixes:
            cur.execute('UPDATE regulatory_provisions SET pdf_page = %s WHERE id = %s',
                        (correct_page, row_id))
        conn.commit()
        print('Done!')

    # Verify
    print('\n=== Verification ===')
    cur.execute('''
        SELECT pdf_page, pdf_page_image_url, LEFT(provision_text, 50)
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%_4.1_%'
        ORDER BY pdf_page, pdf_page_image_url
        LIMIT 10
    ''')
    for pdf_page, url, text in cur.fetchall():
        match = re.search(r'page_(\d+)\.', url)
        url_page = int(match.group(1)) if match else None
        print(f'  pdf_page={pdf_page}, url_page={url_page}: {text[:40]}...')

    conn.close()


if __name__ == '__main__':
    main()
