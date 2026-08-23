#!/usr/bin/env python3
"""DQ-18 FIX: Calculate pdf_page by grouping on section NUMBER.

Previous approaches failed because:
1. Grouping by full URL filename - truncation variants treated as separate sections
2. Grouping by v2_dcp_part - Parts with multiple section PDFs lumped together

This script extracts the section number from the URL (e.g., "2_6", "4_1", "2_18")
and groups by that, so truncation variants get merged correctly.

Each unique section number within a council's DCP = one PDF file.
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
    """Extract section number and page from URL.

    Examples:
        '.../marr_Marrickville_DCP_2011_-_2_6_Acoustic_and_V_page_5.png' -> ('2_6', 5)
        '.../marr_Marrickville_DCP_2011_-_4.1_Low_Density_Res_page_3.png' -> ('4.1', 3)
        '.../marr_Marrickville_DCP_2011_-_9_42_Marrickville_page_5.png' -> ('9_42', 5)
    """
    if not url:
        return None

    # Extract page number
    page_match = re.search(r'page_(\d+)\.', url)
    if not page_match:
        return None
    page = int(page_match.group(1))

    # Extract section number - look for patterns like _2_6_, _4.1_, _9_42_
    # After "DCP_2011_-_" or "DCP_-_"
    section_match = re.search(r'DCP_(?:2011_)?-_(\d+(?:[._]\d+)?)', url)
    if section_match:
        section = section_match.group(1)
        # Normalize: replace . with _ for consistency
        section = section.replace('.', '_')
        return section, page

    return None


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 FIX: GROUP BY SECTION NUMBER')
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

    # Group by section number
    sections = defaultdict(list)
    skipped = 0
    for row_id, pdf_page, url in rows:
        result = extract_section_and_page(url)
        if result:
            section, url_page = result
            sections[section].append((row_id, pdf_page, url_page, url))
        else:
            skipped += 1

    print(f'Unique section numbers: {len(sections)}')
    print(f'Skipped (no section match): {skipped}')
    print()

    # Calculate fixes for each section
    all_fixes = []
    for section, provisions in sorted(sections.items(), key=lambda x: (len(x[0]), x[0])):
        url_pages = [p[2] for p in provisions]
        min_url_page = min(url_pages)
        max_url_page = max(url_pages)

        # Count URL filename variants in this section
        url_prefixes = set()
        for _, _, _, url in provisions:
            match = re.search(r'/([^/]+)_page_', url)
            if match:
                url_prefixes.add(match.group(1)[-30:])

        section_fixes = []
        for row_id, current_pdf_page, url_page, url in provisions:
            relative_page = url_page - min_url_page + 1
            if current_pdf_page != relative_page:
                section_fixes.append((row_id, relative_page, current_pdf_page))

        # Show section info
        status = f'Fixing {len(section_fixes)}' if section_fixes else 'OK'
        variants = f', {len(url_prefixes)} URL variants' if len(url_prefixes) > 1 else ''
        print(f'Section {section}: {len(provisions)} provisions, pages {min_url_page}-{max_url_page}{variants} - {status}')

        if section_fixes:
            for row_id, new, old in section_fixes[:2]:
                print(f'    ID {row_id}: pdf_page {old} -> {new}')
            all_fixes.extend(section_fixes)

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

    # Verify
    print('\n=== Verification ===')
    for test_section in ['2_6', '2_18', '4_1']:
        cur.execute('''
            SELECT pdf_page, pdf_page_image_url
            FROM regulatory_provisions
            WHERE document_id LIKE '%Marrickville%'
              AND pdf_page_image_url LIKE %s
            ORDER BY pdf_page
            LIMIT 3
        ''', (f'%_{test_section}_%',))
        results = cur.fetchall()
        if results:
            print(f'Section {test_section}:')
            for pdf_page, url in results:
                match = re.search(r'page_(\d+)\.', url)
                url_page = int(match.group(1)) if match else None
                print(f'  pdf_page={pdf_page}, url_page={url_page}')

    conn.close()
    print('\nDone!')


if __name__ == '__main__':
    main()
