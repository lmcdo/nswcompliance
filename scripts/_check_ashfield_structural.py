#!/usr/bin/env python3
"""Check v2_structural_category population for Ashfield provisions."""
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
    SELECT v2_structural_category, COUNT(*)
    FROM regulatory_provisions
    WHERE source_council = 'ashfield' AND is_current = true
    GROUP BY v2_structural_category
    ORDER BY COUNT(*) DESC
""")
print("v2_structural_category distribution:")
for row in cur.fetchall():
    print(f"  {str(row[0]):30s} {row[1]}")

print()
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council = 'ashfield' AND is_current = true
      AND v2_structural_category IS NULL
""")
null_count = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council = 'ashfield' AND is_current = true
""")
total = cur.fetchone()[0]
print(f"Total: {total}, NULL structural_category: {null_count}")

cur.close()
conn.close()
