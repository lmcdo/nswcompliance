#!/usr/bin/env python3
"""Show sample provisions without markers to understand the data."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("SAMPLE LEICHHARDT PROVISIONS WITHOUT MARKERS")
print("="*70)

cur.execute("""
    SELECT id, v2_dcp_part, v2_topic, pdf_page, LEFT(provision_text, 400)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (v2_marker IS NULL OR v2_marker = '')
    LIMIT 15
""")

for prov_id, part, topic, page, text in cur.fetchall():
    print(f"\n--- ID {prov_id} ---")
    print(f"Part: {part} | Topic: {topic} | Page: {page}")
    print(f"Text: {text}")
    print()

conn.close()
