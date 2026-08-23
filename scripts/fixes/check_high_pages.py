#!/usr/bin/env python3
"""Check provisions with high page numbers."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check provisions with high page numbers
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 80) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%8.0_Heritage%'
      AND pdf_page > 100
    ORDER BY pdf_page DESC
    LIMIT 20
''')

print('Provisions with pdf_page > 100:')
print('=' * 80)
for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else 0
    # Get file prefix
    prefix_match = re.search(r'/([^/]+)_page_', url)
    prefix = prefix_match.group(1)[-35:] if prefix_match else 'unknown'
    print(f'ID {row_id}: pdf={pdf_page}, url={url_page}')
    print(f'  file: ...{prefix}')
    print(f'  text: {text[:55]}...')
    print()

# Also check what file groups exist
print('\n\nAll file groups with their page ranges:')
print('=' * 80)
cur.execute('''
    SELECT
        SUBSTRING(pdf_page_image_url FROM '/([^/]+)_page_') as file_prefix,
        MIN(pdf_page) as min_pdf,
        MAX(pdf_page) as max_pdf,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%8.0_Heritage%'
    GROUP BY file_prefix
    ORDER BY file_prefix
''')

for prefix, min_pdf, max_pdf, count in cur.fetchall():
    if prefix:
        short = prefix[-40:] if len(prefix) > 40 else prefix
        print(f'{short}')
        print(f'  pdf_page: {min_pdf}-{max_pdf} ({count} provisions)')

conn.close()
