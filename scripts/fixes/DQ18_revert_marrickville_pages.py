#!/usr/bin/env python3
"""DQ-18 REVERT: Restore Marrickville pdf_page to relative page numbers.

The previous fix incorrectly set pdf_page to absolute page numbers from URLs.
This script calculates the correct relative page numbers per section.

Relative page = url_page - section_min_page + 1
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2
from collections import defaultdict

SUPABASE_DB = os.environ['DATABASE_URL']

def extract_section_and_page(url: str) -> tuple[str, int] | None:
    """Extract section identifier and page number from URL."""
    if not url:
        return None
    match = re.search(r'/([^/]+)_page_(\d+)\.png', url)
    if match:
        return match.group(1), int(match.group(2))
    return None

def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 REVERT: RESTORE MARRICKVILLE RELATIVE PAGE NUMBERS')
    print('=' * 60)

    # Get all Marrickville provisions with URLs
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    ''')
    rows = cur.fetchall()
    print(f'\nTotal Marrickville provisions with URLs: {len(rows)}')

    # Group by section (extract from URL filename)
    sections = defaultdict(list)
    for row_id, pdf_page, url in rows:
        result = extract_section_and_page(url)
        if result:
            section, url_page = result
            sections[section].append((row_id, pdf_page, url_page))

    print(f'Unique sections: {len(sections)}')

    # Calculate section offsets and fix pdf_page values
    fixes = []
    for section, provisions in sections.items():
        url_pages = [p[2] for p in provisions]
        min_page = min(url_pages)

        for row_id, current_pdf_page, url_page in provisions:
            relative_page = url_page - min_page + 1
            if current_pdf_page != relative_page:
                fixes.append((row_id, relative_page, current_pdf_page, section))

    print(f'Provisions needing correction: {len(fixes)}')

    if not fixes:
        print('\nNo corrections needed!')
        conn.close()
        return

    # Show sample of fixes
    print('\nSample fixes (first 10):')
    for row_id, new_page, old_page, section in fixes[:10]:
        print(f'  ID {row_id}: pdf_page {old_page} -> {new_page} ({section[:30]}...)')

    # Apply fixes
    print(f'\nApplying {len(fixes)} fixes...')
    for row_id, relative_page, _, _ in fixes:
        cur.execute('''
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        ''', (relative_page, row_id))

    conn.commit()
    print(f'Fixed {len(fixes)} provisions')

    # Verify - check a known landscaping provision
    cur.execute('''
        SELECT pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url LIKE '%Landscaping%'
        LIMIT 5
    ''')
    print('\nVerification (Landscaping provisions):')
    for pdf_page, url in cur.fetchall():
        result = extract_section_and_page(url)
        if result:
            _, url_page = result
            print(f'  pdf_page={pdf_page}, url contains page_{url_page}')

    conn.close()
    print('\nDone!')

if __name__ == '__main__':
    main()
