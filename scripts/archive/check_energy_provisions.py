#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("Energy provisions:")
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part, v2_marker, LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_topic = 'energy'
    AND v2_is_actionable = true
    AND document_id ILIKE '%Leichhardt%'
    ORDER BY pdf_page, id
    LIMIT 20
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: page={r[1]}, part={r[3]}, marker={r[4]}")
    print(f"  url: {r[2]}")
    print(f"  text: {r[5]}...")
    print()

cur.close()
conn.close()
