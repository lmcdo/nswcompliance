#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("Part E water provisions:")
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_marker, LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part E'
    AND v2_topic = 'water'
    AND v2_is_actionable = true
    ORDER BY pdf_page, id
    LIMIT 20
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: page={r[1]}, url={r[2]}")
    print(f"  marker={r[3]}")
    print(f"  text: {r[4]}...")
    print()

cur.close()
conn.close()
