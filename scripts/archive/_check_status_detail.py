#!/usr/bin/env python3
"""Check extraction status vs needs_llm breakdown."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# The pipeline marks needs_llm provisions as review_needed status
# Check how many review_needed actually have numeric_check compliance_type
cur.execute("""
    SELECT v2_extraction_status, COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND v2_extraction_status IS NOT NULL
    GROUP BY v2_extraction_status
""")
print("=== Overall status ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check what's NOT yet processed (no status)
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND v2_is_actionable = true AND v2_extraction_status IS NULL
""")
print(f"\nActionable with NO extraction status: {cur.fetchone()[0]}")

# Count provisions not yet in extraction pipeline scope (not actionable)
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND (v2_is_actionable = false OR v2_is_actionable IS NULL)
""")
print(f"Not actionable (excluded from pipeline): {cur.fetchone()[0]}")

cur.close()
conn.close()
