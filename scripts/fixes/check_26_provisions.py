#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import os
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Check section 2.6 Acoustic provisions
cur.execute("""
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE document_id LIKE '%Marrickville%'
      AND pdf_page_image_url LIKE '%2_6_Acoustic%'
    ORDER BY pdf_page
    LIMIT 15
""")

print('Section 2.6 Acoustic provisions:')
for row in cur.fetchall():
    url_page = row[2].split('page_')[1].split('.')[0] if row[2] and 'page_' in row[2] else '?'
    print(f'  id={row[0]} | pdf_page={row[1]} | url_page={url_page} | {row[3][:60]}...')

print()

# Check what the UI would query for Part 2
cur.execute("""
    SELECT pdf_page, COUNT(*), array_agg(DISTINCT
        CASE
            WHEN pdf_page_image_url LIKE '%2_5_Equity%' THEN '2.5'
            WHEN pdf_page_image_url LIKE '%2_6_Acoustic%' THEN '2.6'
            WHEN pdf_page_image_url LIKE '%2_7_Solar%' THEN '2.7'
            WHEN pdf_page_image_url LIKE '%2_8_Social%' THEN '2.8'
            WHEN pdf_page_image_url LIKE '%2_10_Parking%' THEN '2.10'
            ELSE 'other'
        END
    )
    FROM regulatory_provisions
    WHERE document_id LIKE '%Marrickville%'
      AND v2_dcp_part = 'Part 2'
    GROUP BY pdf_page
    ORDER BY pdf_page
    LIMIT 20
""")

print('Part 2 provisions grouped by pdf_page:')
for row in cur.fetchall():
    sections = ', '.join(sorted(set(row[2]))) if row[2] else '?'
    print(f'  Page {row[0]}: {row[1]} provisions from sections: {sections}')

conn.close()
