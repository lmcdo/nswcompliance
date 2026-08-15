#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("Heritage provisions - distinct v2_dcp_part values:")
cur.execute('''
    SELECT DISTINCT v2_dcp_part, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_topic = 'heritage'
    AND v2_is_actionable = true
    AND document_id ILIKE '%Leichhardt%'
    GROUP BY v2_dcp_part
    ORDER BY v2_dcp_part
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n\nSample heritage provisions:")
cur.execute('''
    SELECT id, v2_dcp_part, pdf_page, document_id, LEFT(provision_text, 80)
    FROM regulatory_provisions
    WHERE v2_topic = 'heritage'
    AND v2_is_actionable = true
    AND document_id ILIKE '%Leichhardt%'
    ORDER BY pdf_page
    LIMIT 10
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: part={r[1]}, page={r[2]}")
    print(f"  doc_id: {r[3]}")
    print(f"  text: {r[4]}...")
    print()

cur.close()
conn.close()
