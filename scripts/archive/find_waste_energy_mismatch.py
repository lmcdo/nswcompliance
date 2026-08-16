#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find provision with waste management text classified as energy
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part, v2_topic, v2_marker, provision_text
    FROM regulatory_provisions
    WHERE v2_topic = 'energy'
    AND v2_is_actionable = true
    AND provision_text ILIKE '%waste management system%'
''')

print("Energy provisions with 'waste management system':")
for r in cur.fetchall():
    print(f"ID {r[0]}: page={r[1]}, part={r[3]}, topic={r[4]}, marker={r[5]}")
    print(f"  url: {r[2]}")
    print(f"  text: {r[6][:200]}...")
    print()

# Also check for part-g URL in energy provisions
cur.execute('''
    SELECT id, pdf_page, pdf_page_image_url, v2_dcp_part, v2_topic
    FROM regulatory_provisions
    WHERE v2_topic = 'energy'
    AND v2_is_actionable = true
    AND pdf_page_image_url ILIKE '%part-g%'
''')

print("\nEnergy provisions with Part G URL:")
for r in cur.fetchall():
    print(f"ID {r[0]}: page={r[1]}, part={r[3]}, url={r[2]}")

cur.close()
conn.close()
