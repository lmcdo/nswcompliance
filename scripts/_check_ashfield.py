#!/usr/bin/env python3
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Ashfield registry state
cur.execute("""
    SELECT chapter_key, is_active, needs_extraction, r2_current_path IS NOT NULL as has_r2,
           last_extracted_at
    FROM dcp_chapter_registry
    WHERE council = 'ashfield'
    ORDER BY chapter_key
""")
print("=== Ashfield Registry ===")
for row in cur.fetchall():
    print(f"  {row[0]}: active={row[1]}, needs_extract={row[2]}, has_r2={row[3]}, last_extracted={row[4]}")

# Check if ashfield has non-current provisions (soft-deleted)
cur.execute("""
    SELECT is_current, COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
    GROUP BY is_current
""")
print("\n=== Ashfield provisions by is_current ===")
for row in cur.fetchall():
    print(f"  is_current={row[0]}: {row[1]}")

cur.close()
conn.close()
