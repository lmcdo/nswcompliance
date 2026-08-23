#!/usr/bin/env python3
"""DQ-18 FIX: Calculate pdf_page excluding TOC pages from min calculation.

The issue: TOC pages (containing "..........") have low URL page numbers
but aren't the first content page. This skews the min_url calculation.

Fix: Exclude provisions with TOC-style text from min calculation,
but still set their pdf_page based on the content pages' min.
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
    """Extract section number and page from URL."""
    if not url:
        return None
    page_match = re.search(r'page_(\d+)\.', url)
    if not page_match:
        return None
    page = int(page_match.group(1))

    section_match = re.search(r'DCP_(?:2011_)?-_(\d+(?:[._]\d+)?)', url)
    if section_match:
        section = section_match.group(1).replace('.', '_')
        return section, page
    return None


def is_toc_entry(text: str) -> bool:
    """Check if provision text looks like a TOC entry."""
    if not text:
        return False
    # TOC entries typically have dots like "Section Name.......... 5"
    return '........' in text or '. . . . .' in text


def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 FIX: EXCLUDE TOC PAGES FROM MIN CALCULATION')
    print('=' * 60)

    # Get all Marrickville provisions
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url, provision_text
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    ''')
    rows = cur.fetchall()
    print(f'\nTotal provisions: {len(rows)}')

    # Group by section, separating TOC from content
    sections = defaultdict(lambda: {'toc': [], 'content': []})

    for row_id, pdf_page, url, text in rows:
        result = extract_section_and_page(url)
        if result:
            section, url_page = result
            entry = (row_id, pdf_page, url_page, text[:100] if text else '')
            if is_toc_entry(text):
                sections[section]['toc'].append(entry)
            else:
                sections[section]['content'].append(entry)

    print(f'Sections with TOC entries: {sum(1 for s in sections.values() if s["toc"])}')

    # Calculate fixes - use min from CONTENT pages only
    all_fixes = []
    for section, data in sorted(sections.items()):
        content = data['content']
        toc = data['toc']

        if not content:
            continue

        # Find min URL page from CONTENT only (exclude TOC)
        content_url_pages = [p[2] for p in content]
        min_content_url = min(content_url_pages)

        # Show sections where TOC affects the calculation
        if toc:
            toc_url_pages = [p[2] for p in toc]
            min_toc_url = min(toc_url_pages)
            if min_toc_url < min_content_url:
                print(f'\nSection {section}:')
                print(f'  TOC pages: {sorted(set(toc_url_pages))} (excluded)')
                print(f'  Content min: {min_content_url} (used for calculation)')

        # Fix CONTENT provisions using content min
        # TOC pages get pdf_page=0 (they're before page 1)
        for row_id, current_pdf_page, url_page, text in content:
            relative_page = url_page - min_content_url + 1
            if current_pdf_page != relative_page:
                all_fixes.append((row_id, relative_page, current_pdf_page, section))

        # TOC pages: set to 1 (they're part of the document intro)
        for row_id, current_pdf_page, url_page, text in toc:
            if current_pdf_page != 1:
                all_fixes.append((row_id, 1, current_pdf_page, section))

    print(f'\nTotal fixes needed: {len(all_fixes)}')

    if not all_fixes:
        print('\nNo fixes needed!')
        conn.close()
        return

    # Apply fixes
    print(f'\nApplying {len(all_fixes)} fixes...')
    for row_id, relative_page, old_page, section in all_fixes:
        cur.execute('UPDATE regulatory_provisions SET pdf_page = %s WHERE id = %s',
                    (relative_page, row_id))

    conn.commit()
    print('Done!')

    # Verify Part 4.1
    print('\n=== Verification: Part 4.1 ===')
    cur.execute('''
        SELECT pdf_page, pdf_page_image_url, LEFT(provision_text, 60)
        FROM regulatory_provisions
        WHERE pdf_page_image_url LIKE '%_4.1_%'
        ORDER BY pdf_page
        LIMIT 10
    ''')
    for pdf_page, url, text in cur.fetchall():
        match = re.search(r'page_(\d+)\.', url)
        url_page = int(match.group(1)) if match else None
        is_toc = 'TOC' if is_toc_entry(text) else ''
        print(f'  pdf_page={pdf_page}, url_page={url_page} {is_toc}: {text[:50]}...')

    conn.close()


if __name__ == '__main__':
    main()
