#!/usr/bin/env python3
"""Verify current page number state for Marrickville provisions."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2
from collections import defaultdict

SUPABASE_DB = os.environ['DATABASE_URL']

conn = psycopg2.connect(SUPABASE_DB)
cur = conn.cursor()

# Check Part 2 - should have separate page numbering per section
print('=== Part 2 (multiple section PDFs) ===')
cur.execute('''
    SELECT pdf_page, pdf_page_image_url
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part 2'
      AND pdf_page_image_url IS NOT NULL
    ORDER BY pdf_page_image_url
''')

sections = defaultdict(list)
for pdf_page, url in cur.fetchall():
    match = re.search(r'/([^/]+)_page_(\d+)\.png', url)
    if match:
        section = match.group(1)
        url_page = int(match.group(2))
        sections[section].append((pdf_page, url_page))

print(f'Part 2 has {len(sections)} URL sections')
for section, provs in sorted(sections.items()):
    pdf_pages = [p[0] for p in provs]
    url_pages = [p[1] for p in provs]
    print(f'  {section[-40:]}')
    print(f'    pdf_page: {min(pdf_pages)}-{max(pdf_pages)}, url_page: {min(url_pages)}-{max(url_pages)}')
    # First provision in section should have pdf_page=1 if it's a separate PDF
    first = min(provs, key=lambda x: x[1])  # provision with lowest url_page
    status = 'OK' if first[0] == 1 else f'WRONG (pdf_page={first[0]}, should be 1)'
    print(f'    First provision: {status}')

print()
print('=== Part 4.1 (single PDF) ===')
cur.execute('''
    SELECT pdf_page, pdf_page_image_url
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part 4.1'
      AND pdf_page_image_url IS NOT NULL
    ORDER BY pdf_page
    LIMIT 5
''')
for pdf_page, url in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else None
    print(f'  pdf_page={pdf_page}, url_page={url_page}')

conn.close()
