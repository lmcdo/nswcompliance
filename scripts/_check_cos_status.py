#!/usr/bin/env python3
"""Check City of Sydney extraction status."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check registry status
cur.execute("""
    SELECT chapter_key, needs_extraction, last_extracted_at
    FROM dcp_chapter_registry
    WHERE council = 'city_of_sydney'
    ORDER BY sort_order
""")
print("Registry status:")
for r in cur.fetchall():
    print(f"  {r[0]:<35} needs_extract={r[1]} last={r[2]}")

# Check provision counts
cur.execute("""
    SELECT source_chapter_key, COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
    GROUP BY source_chapter_key
    ORDER BY source_chapter_key
""")
print("\nProvision counts:")
for r in cur.fetchall():
    print(f"  {r[0]:<35} {r[1]}")

cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
""")
print(f"\nTotal: {cur.fetchone()[0]}")

cur.close()
conn.close()
