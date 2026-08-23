#!/usr/bin/env python3
"""Check hca_12 and hca_13 provisions."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

for hca in ['hca_12', 'hca_13']:
    print(f'\n{hca} provisions:')
    print('=' * 70)
    cur.execute('''
        SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 80) as text
        FROM regulatory_provisions
        WHERE v2_heritage_hca = %s
        ORDER BY pdf_page
        LIMIT 15
    ''', (hca,))

    for row_id, pdf_page, url, text in cur.fetchall():
        match = re.search(r'page_(\d+)\.', url or '')
        url_page = int(match.group(1)) if match else 0
        file_match = re.search(r'/([^/]+)_page_', url or '')
        file_prefix = file_match.group(1)[-30:] if file_match else 'unknown'
        print(f'ID {row_id}: pdf={pdf_page}, url={url_page}')
        print(f'  file: ...{file_prefix}')
        print(f'  text: {text[:50]}...')
        print()

conn.close()
