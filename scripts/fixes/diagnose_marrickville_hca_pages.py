#!/usr/bin/env python3
"""Diagnose Marrickville HCA provision page numbers.

Check what pdf_page and pdf_page_image_url values exist for provisions
in v2_heritage_hca that relate to Marrickville.
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

    print('=' * 70)
    print('DIAGNOSE MARRICKVILLE HCA PROVISION PAGE NUMBERS')
    print('=' * 70)

    # Query Marrickville HCA provisions (Part 8 Heritage)
    cur.execute('''
        SELECT
            id,
            pdf_page,
            pdf_page_image_url,
            v2_heritage_hca,
            v2_dcp_part,
            document_id,
            LEFT(provision_text, 80) as text_preview
        FROM regulatory_provisions
        WHERE (
            document_id ILIKE '%Marrickville%Part%8%'
            OR document_id ILIKE '%Marrickville%Heritage%'
            OR (v2_dcp_part = 'Part 8' AND document_id ILIKE '%Marrickville%')
        )
        AND pdf_page_image_url IS NOT NULL
        ORDER BY pdf_page_image_url, pdf_page
        LIMIT 50
    ''')
    rows = cur.fetchall()

    print(f'\nMarrickville Part 8 Heritage provisions: {len(rows)}')
    print()

    # Group by URL prefix to see section groupings
    url_groups = {}
    for row in rows:
        row_id, pdf_page, url, hca, part, doc_id, text = row
        # Extract page from URL
        page_match = re.search(r'page_(\d+)\.', url or '')
        url_page = int(page_match.group(1)) if page_match else None

        # Get URL prefix (before page_)
        prefix_match = re.search(r'([^/]+)_page_\d+\.', url or '')
        prefix = prefix_match.group(1)[-40:] if prefix_match else 'unknown'

        if prefix not in url_groups:
            url_groups[prefix] = []
        url_groups[prefix].append({
            'id': row_id,
            'pdf_page': pdf_page,
            'url_page': url_page,
            'hca': hca,
            'text': text[:60] if text else ''
        })

    # Show each URL group
    for prefix, provisions in sorted(url_groups.items()):
        print(f'\n--- URL group: ...{prefix}_page_N.png ---')
        url_pages = [p['url_page'] for p in provisions if p['url_page']]
        pdf_pages = [p['pdf_page'] for p in provisions if p['pdf_page']]

        if url_pages and pdf_pages:
            print(f'URL pages: {min(url_pages)}-{max(url_pages)}')
            print(f'pdf_page values: {min(pdf_pages)}-{max(pdf_pages)}')

            # Show offset
            # If pdf_page should be relative (1 for first page), offset = min(url_page) - 1
            expected_offset = min(url_pages) - 1
            print(f'Expected offset: {expected_offset} (url_page {min(url_pages)} should be pdf_page 1)')

        print(f'Sample provisions:')
        for p in provisions[:5]:
            offset_note = ''
            if p['url_page'] and p['pdf_page']:
                actual_relative = p['url_page'] - (min(url_pages) - 1) if url_pages else 0
                if actual_relative != p['pdf_page']:
                    offset_note = f' [WRONG: should be {actual_relative}]'
            print(f"  ID {p['id']}: pdf_page={p['pdf_page']}, url_page={p['url_page']}{offset_note}")
            print(f"      HCA: {p['hca']}, text: {p['text']}...")

    # Also check by v2_heritage_hca directly
    print('\n\n' + '=' * 70)
    print('CHECK BY v2_heritage_hca (Marrickville HCAs)')
    print('=' * 70)

    cur.execute('''
        SELECT DISTINCT v2_heritage_hca
        FROM regulatory_provisions
        WHERE v2_heritage_hca IS NOT NULL
          AND document_id ILIKE '%Marrickville%'
    ''')
    hcas = [r[0] for r in cur.fetchall()]
    print(f'\nMarrickville HCAs in database: {hcas}')

    for hca in hcas[:3]:  # Check first 3
        cur.execute('''
            SELECT pdf_page, pdf_page_image_url
            FROM regulatory_provisions
            WHERE v2_heritage_hca = %s
            ORDER BY pdf_page
            LIMIT 10
        ''', (hca,))
        hca_rows = cur.fetchall()
        if hca_rows:
            print(f'\n{hca}:')
            for pdf_page, url in hca_rows[:5]:
                page_match = re.search(r'page_(\d+)\.', url or '')
                url_page = int(page_match.group(1)) if page_match else None
                print(f'  pdf_page={pdf_page}, url_page={url_page}')

    conn.close()
    print('\n\nDone!')


if __name__ == '__main__':
    main()
