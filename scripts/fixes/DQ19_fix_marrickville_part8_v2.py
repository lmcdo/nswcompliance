#!/usr/bin/env python3
"""DQ-19 FIX v2: Marrickville Part 8 Heritage pdf_page values.

CORRECT APPROACH: Group by URL file prefix, calculate relative page within each PDF.
Each Part 8 subsection is a separate PDF that starts at page 1.

Formula: pdf_page = url_page - min(url_page for this PDF) + 1

This is the same logic as DQ18_fix_by_section_number.py but for Part 8 specifically.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2
from collections import defaultdict

SUPABASE_DB = os.environ['DATABASE_URL']


def extract_file_prefix_and_page(url: str) -> tuple[str, int] | None:
    """Extract the file prefix (everything before _page_N) and page number."""
    if not url:
        return None

    # Pattern: .../<filename>_page_N.png
    match = re.search(r'/([^/]+)_page_(\d+)\.', url)
    if match:
        prefix = match.group(1)
        page = int(match.group(2))
        return prefix, page

    return None


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 70)
    print('DQ-19 FIX v2: MARRICKVILLE PART 8 HERITAGE PAGE NUMBERS')
    print('Grouping by PDF file prefix, calculating relative page within each')
    print('=' * 70)

    # Get all Marrickville Part 8 Heritage provisions
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE (
            pdf_page_image_url LIKE '%8.0_Heritage%'
            OR pdf_page_image_url LIKE '%8_Heritage%'
            OR (document_id ILIKE '%Marrickville%Part%8%' AND pdf_page_image_url IS NOT NULL)
        )
    ''')
    rows = cur.fetchall()

    print(f'\nFound {len(rows)} Marrickville Part 8 Heritage provisions')

    # Group by file prefix
    by_prefix = defaultdict(list)
    skipped = 0
    for row_id, pdf_page, url in rows:
        result = extract_file_prefix_and_page(url)
        if result:
            prefix, url_page = result
            by_prefix[prefix].append((row_id, pdf_page, url_page, url))
        else:
            skipped += 1

    print(f'Unique PDF files: {len(by_prefix)}')
    print(f'Skipped (no match): {skipped}')
    print()

    # Calculate fixes for each PDF file
    all_fixes = []
    for prefix in sorted(by_prefix.keys()):
        provisions = by_prefix[prefix]
        url_pages = [p[2] for p in provisions]
        min_url_page = min(url_pages)
        max_url_page = max(url_pages)

        fixes = []
        for row_id, current_pdf_page, url_page, url in provisions:
            # Relative page = url_page - min + 1
            relative_page = url_page - min_url_page + 1

            if current_pdf_page != relative_page:
                fixes.append((row_id, current_pdf_page, relative_page))

        # Show info
        short_prefix = prefix[-50:] if len(prefix) > 50 else prefix
        status = f'FIX {len(fixes)}' if fixes else 'OK'
        print(f'{short_prefix}')
        print(f'  URL pages {min_url_page}-{max_url_page} ({len(provisions)} provs) -> {status}')

        if fixes:
            all_fixes.extend(fixes)

    print()
    print(f'Total provisions to fix: {len(all_fixes)}')

    if not all_fixes:
        print('\nNo fixes needed!')
        conn.close()
        return

    # Show samples
    print('\nSample fixes:')
    for row_id, old, new in all_fixes[:10]:
        print(f'  ID {row_id}: pdf_page {old} -> {new}')

    # Apply fixes
    print(f'\nApplying {len(all_fixes)} fixes...')
    for row_id, old, new in all_fixes:
        cur.execute('''
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        ''', (new, row_id))

    conn.commit()
    print(f'Fixed {len(all_fixes)} provisions')

    # Verify a sample
    print('\n=== Verification ===')
    for prefix in list(by_prefix.keys())[:3]:
        provisions = by_prefix[prefix]
        min_url = min(p[2] for p in provisions)
        # Check first page of this PDF
        cur.execute('''
            SELECT id, pdf_page, pdf_page_image_url
            FROM regulatory_provisions
            WHERE pdf_page_image_url LIKE %s
            ORDER BY pdf_page
            LIMIT 2
        ''', (f'%{prefix[-30:]}%page_{min_url}%',))
        results = cur.fetchall()
        short_prefix = prefix[-40:] if len(prefix) > 40 else prefix
        print(f'\n{short_prefix} (min url_page={min_url}):')
        for row_id, pdf_page, url in results:
            print(f'  ID {row_id}: pdf_page={pdf_page} (should be 1)')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
