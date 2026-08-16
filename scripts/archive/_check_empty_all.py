#!/usr/bin/env python3
"""Check all councils for empty/near-empty provisions that should be deactivated."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT source_council, id, section_header, LENGTH(provision_text) as chars,
           LEFT(provision_text, 100) as snippet
    FROM regulatory_provisions
    WHERE is_current = true AND source_council IS NOT NULL
      AND LENGTH(provision_text) < 50
    ORDER BY source_council, chars
""")
rows = cur.fetchall()
print(f"{len(rows)} provisions under 50 chars across all councils:\n")
for r in rows:
    print(f"  {r[0]:15s} ID {r[1]:6d} | {r[3]:3d} chars | {(r[2] or '')[:40]:40s} | {r[4]}")

cur.close()
conn.close()
