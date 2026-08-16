#!/usr/bin/env python3
"""Check Part G page numbers in database."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find Norton Street / cycle parking provisions in Part G
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, provision_text
    FROM regulatory_provisions
    WHERE v2_dcp_part = %s
    AND provision_text ILIKE %s
    LIMIT 5
''', ('Part G', '%cycle parking%'))

print("Cycle parking provisions:")
for row in cur.fetchall():
    print(f'ID: {row[0]}')
    print(f'pdf_page: {row[1]}')
    print(f'url: {row[2]}')
    print(f'text: {row[3][:100]}...')
    print()

# Also check first few Part G provisions
print("\n\nFirst Part G provisions by page:")
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, LEFT(provision_text, 80) as text
    FROM regulatory_provisions
    WHERE v2_dcp_part = %s
    ORDER BY pdf_page, id
    LIMIT 10
''', ('Part G',))

for row in cur.fetchall():
    print(f'Page {row[1]}: {row[3]}...')

cur.close()
conn.close()
