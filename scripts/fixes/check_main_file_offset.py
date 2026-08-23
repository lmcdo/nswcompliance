#!/usr/bin/env python3
"""Check what the correct offset should be for the main 8.0_Heritage file."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print('Main file marr_Marrickville_DCP_2011_-_8.0_Heritage analysis:')
print('=' * 70)

# Find provisions with section headers to identify where content starts
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
      AND (provision_text LIKE '8.1 Introduction%' OR provision_text LIKE '8.2.1 %')
    ORDER BY pdf_page
    LIMIT 10
''')

print('\nLooking for "8.1 Introduction" or "8.2.1" to find content start:')
for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url or '')
    url_page = int(match.group(1)) if match else 0
    print(f'ID {row_id}: pdf_page={pdf_page}, url_page={url_page}')
    print(f'  {text[:70]}...')

# Check lowest url_page provisions
print('\n\nLowest url_page provisions:')
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%marr_Marrickville_DCP_2011_-_8.0_Heritage_page_%'
    ORDER BY pdf_page
    LIMIT 15
''')

for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url or '')
    url_page = int(match.group(1)) if match else 0
    print(f'url={url_page}, pdf={pdf_page}: {text[:55]}...')

conn.close()
