#!/usr/bin/env python3
"""Check what's on early url pages of Marrickville Part 8 Heritage."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check provisions from early url pages (2-20) of the Part subgroup
cur.execute('''
    SELECT pdf_page, pdf_page_image_url, LEFT(provision_text, 120) as text
    FROM regulatory_provisions
    WHERE pdf_page_image_url LIKE '%8.0_Heritage_-_Part_page_%'
    ORDER BY pdf_page_image_url
    LIMIT 25
''')

print("URL pages 2-20 of 8.0_Heritage_-_Part:")
print("=" * 80)
for pdf_page, url, text in cur.fetchall():
    match = re.search(r'page_(\d+)\.', url)
    url_page = int(match.group(1)) if match else 0
    # Detect TOC-like content
    is_toc = '......' in text or 'Contents' in text or (text.count('.') > 10 and len(text) < 80)
    toc_marker = ' [TOC]' if is_toc else ''
    print(f'url={url_page:2d}, pdf={pdf_page:2d}{toc_marker}: {text[:65]}...')

conn.close()
