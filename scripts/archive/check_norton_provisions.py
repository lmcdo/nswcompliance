#!/usr/bin/env python3
"""Check Norton Street Part G provisions."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find Norton Street provisions in Part G
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_topic, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE v2_dcp_part = %s
    AND v2_precinct_id ILIKE %s
    ORDER BY pdf_page, id
    LIMIT 20
''', ('Part G', '%norton%'))

print("Norton Street Part G provisions:")
for row in cur.fetchall():
    print(f'ID {row[0]}: page {row[1]}, url={row[2]}, topic={row[3]}')
    print(f'  Text: {row[4]}...')
    print()

cur.close()
conn.close()
