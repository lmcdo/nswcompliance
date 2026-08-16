#!/usr/bin/env python3
"""Check what precinct 70 Norton St should be in."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check Part G precincts
print("Part G Precincts in Leichhardt:")
cur.execute('''
    SELECT DISTINCT v2_precinct_id, LEFT(provision_text, 100) as sample
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_is_actionable = true
    AND v2_precinct_id IS NOT NULL
    ORDER BY v2_precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1][:60]}...")

# Check G2 provisions - is this Old Ampol?
print("\n\nG2 precinct provisions (first few):")
cur.execute('''
    SELECT id, pdf_page, v2_topic, LEFT(provision_text, 150)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_precinct_id = 'G2'
    AND v2_is_actionable = true
    ORDER BY pdf_page
    LIMIT 10
''')
for r in cur.fetchall():
    print(f"  ID {r[0]} page {r[1]} [{r[2]}]: {r[3][:80]}...")

# What provisions are on page 11-12 of Part G?
print("\n\nPart G page 11-12 provisions:")
cur.execute('''
    SELECT id, pdf_page, v2_precinct_id, v2_topic, LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND pdf_page BETWEEN 11 AND 12
    AND v2_is_actionable = true
    ORDER BY pdf_page, id
''')
for r in cur.fetchall():
    print(f"  ID {r[0]} page {r[1]} [{r[2]}] {r[3]}: {r[4][:60]}...")

cur.close()
conn.close()
