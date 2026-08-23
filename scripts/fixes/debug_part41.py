#!/usr/bin/env python3
"""Debug Part 4.1 provision URLs and page numbers."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

conn = psycopg2.connect(SUPABASE_DB)
cur = conn.cursor()

# Get Part 4.1 provisions - check their actual URLs
print('=== Part 4.1 Provisions (by v2_dcp_part) ===')
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 60)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part 4.1'
      AND pdf_page_image_url IS NOT NULL
    ORDER BY pdf_page_image_url
    LIMIT 20
''')

for row_id, pdf_page, url, text in cur.fetchall():
    # Extract URL filename and page
    match = re.search(r'/([^/]+_page_(\d+)\.png)', url)
    if match:
        filename = match.group(1)
        url_page = match.group(2)
        # Check if URL actually contains 4.1 or 4_1
        has_41 = '_4.1_' in url or '_4_1_' in url
        marker = '4.1 URL' if has_41 else 'OTHER URL!'
        print(f'{marker}: pdf_page={pdf_page}, url_page={url_page}')
        print(f'  URL: ...{filename[-50:]}')
        print(f'  Text: {text[:50]}...')
        print()

# Now check provisions whose URL specifically contains _4.1_
print('\n=== Provisions with URL containing _4.1_ ===')
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part, LEFT(provision_text, 50)
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%_4.1_%'
    ORDER BY pdf_page_image_url
    LIMIT 15
''')

for row_id, pdf_page, url, dcp_part, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else None
    print(f'ID {row_id}: pdf_page={pdf_page}, url_page={url_page}, v2_dcp_part={dcp_part}')
    print(f'  Text: {text}...')

conn.close()
