#!/usr/bin/env python3
"""DQ-18 FIX: Calculate pdf_page by grouping on v2_dcp_part.

Previous attempts grouped by URL filename, which caused issues when
the same Part had multiple URL filename variants (due to truncation).

This script groups by v2_dcp_part so all provisions in the same Part
use the same minimum URL page as the offset.

Formula: relative_page = url_page - part_min_url_page + 1
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2
from collections import defaultdict

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
    print('DQ-18 FIX: GROUP BY v2_dcp_part')
    print('=' * 60)

    # Get all Marrickville provisions with URLs
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
          AND v2_dcp_part IS NOT NULL
    ''')
    rows = cur.fetchall()
    print(f'\nTotal Marrickville provisions with URLs and Parts: {len(rows)}')

    # Group by v2_dcp_part (NOT by URL filename)
    parts = defaultdict(list)
    for row_id, pdf_page, url, dcp_part in rows:
        url_page = extract_page_from_url(url)
        if url_page is not None:
            parts[dcp_part].append((row_id, pdf_page, url_page, url))

    print(f'Unique Parts: {len(parts)}')
    print()

    # Calculate fixes for each Part
    all_fixes = []
    for part_name, provisions in sorted(parts.items()):
        url_pages = [p[2] for p in provisions]
        min_url_page = min(url_pages)
        max_url_page = max(url_pages)

        part_fixes = []
        for row_id, current_pdf_page, url_page, url in provisions:
            relative_page = url_page - min_url_page + 1
            if current_pdf_page != relative_page:
                part_fixes.append((row_id, relative_page, current_pdf_page))

        if part_fixes:
            print(f'{part_name}: {len(provisions)} provisions, URL pages {min_url_page}-{max_url_page}')
            print(f'  Fixing {len(part_fixes)} provisions')
            # Show sample
            for row_id, new, old in part_fixes[:2]:
                print(f'    ID {row_id}: pdf_page {old} -> {new}')
            all_fixes.extend(part_fixes)
        else:
            print(f'{part_name}: {len(provisions)} provisions - all correct')

    print()
    print(f'Total provisions to fix: {len(all_fixes)}')

    if not all_fixes:
        print('\nNo fixes needed!')
        conn.close()
        return

    # Apply fixes
    print(f'\nApplying {len(all_fixes)} fixes...')
    for row_id, relative_page, _ in all_fixes:
        cur.execute('''
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        ''', (relative_page, row_id))

    conn.commit()
    print(f'Fixed {len(all_fixes)} provisions')

    # Verify Part 4.1
    print('\n=== Verification: Part 4.1 ===')
    cur.execute('''
        SELECT pdf_page, pdf_page_image_url, LEFT(provision_text, 50)
        FROM regulatory_provisions
        WHERE v2_dcp_part = 'Part 4.1'
          AND pdf_page_image_url IS NOT NULL
        ORDER BY pdf_page
        LIMIT 5
    ''')
    for pdf_page, url, text in cur.fetchall():
        url_page = extract_page_from_url(url)
        print(f'  pdf_page={pdf_page}, url_page={url_page}: {text}...')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
