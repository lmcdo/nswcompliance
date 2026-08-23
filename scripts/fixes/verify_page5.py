#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import re
import os
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check provisions that have URL page_5
cur.execute("""
    SELECT pdf_page, pdf_page_image_url
    FROM regulatory_provisions
    WHERE document_id LIKE '%Marrickville%'
      AND pdf_page_image_url LIKE '%page_5.%'
    LIMIT 20
""")
print('Provisions with URL page_5.png (should have pdf_page=1 for Part 2 sections):')
for row in cur.fetchall():
    url = row[1] or ''
    match = re.search(r'Marrickville_DCP_2011_-_([^/]+)', url)
    section = match.group(1)[:25] if match else '?'
    print(f'  pdf_page={row[0]} | {section}')

conn.close()
