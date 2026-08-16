#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("Part G parking provisions:")
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_topic, v2_precinct_id, LEFT(provision_text, 80)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_topic = 'parking'
    ORDER BY pdf_page
    LIMIT 10
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: page={r[1]}, url={r[2]}")
    print(f"  precinct={r[4]}, text={r[5]}...")
    print()

cur.close()
conn.close()
