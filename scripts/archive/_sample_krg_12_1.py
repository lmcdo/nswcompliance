#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
# Find 12.1 SIGNAGE DESIGN provision
cur.execute("""
    SELECT id, section_header, provision_text
    FROM regulatory_provisions
    WHERE source_council='ku_ring_gai' AND v2_dcp_part='part_12_signage' AND is_current=true
    AND section_header ILIKE '%12.1%'
    LIMIT 1
""")
row = cur.fetchone()
if row:
    print(f"id={row[0]} header={row[1]}")
    print()
    print(row[2])
else:
    print("Not found by header, trying text search...")
    cur.execute("""
        SELECT id, section_header, provision_text
        FROM regulatory_provisions
        WHERE source_council='ku_ring_gai' AND v2_dcp_part='part_12_signage' AND is_current=true
        AND provision_text ILIKE '%12.1 SIGNAGE%'
        LIMIT 1
    """)
    row = cur.fetchone()
    if row:
        print(f"id={row[0]} header={row[1]}")
        print()
        print(row[2])
cur.close()
conn.close()
