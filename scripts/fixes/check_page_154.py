#!/usr/bin/env python3
"""Check what provision has pdf_page=154 and what url_page it corresponds to."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check provisions with pdf_page around 154
print('Provisions with pdf_page near 154:')
print('=' * 80)
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%8.0_Heritage%'
      AND pdf_page BETWEEN 150 AND 160
    ORDER BY pdf_page
''')

for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else 0
    print(f'ID {row_id}: pdf_page={pdf_page}, url_page={url_page}')
    print(f'  text: {text[:70]}...')
    print()

# Check the main file specifically - what's the range?
print('\n\nMain file (marr_Marrickville_DCP_2011_-_8.0_Heritage) details:')
print('=' * 80)
cur.execute('''
    SELECT
        MIN(pdf_page) as min_pdf,
        MAX(pdf_page) as max_pdf,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
''')
row = cur.fetchone()
print(f'pdf_page range: {row[0]}-{row[1]} ({row[2]} provisions)')

# Get url_page range
cur.execute('''
    SELECT pdf_page_image_url
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
''')
urls = [r[0] for r in cur.fetchall()]
url_pages = []
for url in urls:
    match = re.search(r'page_(\d+)\.', url)
    if match:
        url_pages.append(int(match.group(1)))

if url_pages:
    print(f'url_page range: {min(url_pages)}-{max(url_pages)}')
    print(f'Current offset: pdf_page = url_page - {min(url_pages) - 1} (based on min url)')

# Check first few provisions
print('\nFirst provisions (lowest url_page):')
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 80) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
    ORDER BY pdf_page_image_url
    LIMIT 10
''')

for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else 0
    print(f'ID {row_id}: url_page={url_page}, pdf_page={pdf_page}')
    print(f'  {text[:60]}...')

conn.close()
