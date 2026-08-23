#!/usr/bin/env python3
"""Check what HCA 268 Enmore Road Marrickville belongs to and its provisions."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check for Enmore-related HCAs
print('HCAs containing "Enmore":')
print('=' * 80)
cur.execute('''
    SELECT DISTINCT v2_heritage_hca, LEFT(provision_text, 100) as sample
    FROM regulatory_provisions
    WHERE provision_text ILIKE '%Enmore%'
      AND v2_heritage_hca IS NOT NULL
    LIMIT 10
''')

for hca, sample in cur.fetchall():
    print(f'{hca}: {sample[:60]}...')

# Check heritage_conservation_areas table
print('\n\nHCA lookup table entries with "Enmore":')
cur.execute('''
    SELECT h_id, name, db_slug
    FROM heritage_conservation_areas
    WHERE name ILIKE '%Enmore%' OR db_slug ILIKE '%Enmore%'
''')

for h_id, name, db_slug in cur.fetchall():
    print(f'{h_id}: {name} -> db_slug: {db_slug}')

# Check provisions for a likely Enmore HCA
print('\n\nChecking hca_13 (likely Enmore based on numbering):')
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE v2_heritage_hca = 'hca_13'
    LIMIT 10
''')

for row_id, pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url or '')
    url_page = int(match.group(1)) if match else 0
    print(f'ID {row_id}: pdf_page={pdf_page}, url_page={url_page}')
    print(f'  {text[:60]}...')

conn.close()
