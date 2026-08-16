#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Get the exact provision the user is seeing
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part, v2_marker, v2_precinct_id,
           provision_text
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_topic = 'parking'
    AND provision_text ILIKE '%cycle parking%'
    ORDER BY id
''')

for r in cur.fetchall():
    print(f"ID: {r[0]}")
    print(f"pdf_page: {r[1]}")
    print(f"pdf_page_image_url: {r[2]}")
    print(f"v2_dcp_part: {r[3]}")
    print(f"v2_marker: {r[4]}")
    print(f"v2_precinct_id: {r[5]}")
    print(f"text: {r[6][:150]}...")
    print()

cur.close()
conn.close()
