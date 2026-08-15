#!/usr/bin/env python3
"""Check why Ashfield provisions are so large and whether subsection splits fired."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Ashfield: show all provisions with their sizes
print("=== ASHFIELD PROVISION SIZES ===")
cur.execute("""
    SELECT id, source_chapter_key, section_header, LENGTH(provision_text) as chars,
           pdf_page
    FROM regulatory_provisions
    WHERE is_current = true AND source_council = 'ashfield'
    ORDER BY LENGTH(provision_text) DESC
""")
for r in cur.fetchall():
    size_flag = "HUGE" if r[3] > 10000 else "OK" if r[3] < 3000 else "big"
    print(f"  [{size_flag:4s}] {r[3]:6d} chars | {r[1]:30s} | {r[2]}")

# Check: do the section headers show subsection splits?
print("\n=== SUBSECTION SPLIT CHECK ===")
cur.execute("""
    SELECT section_header, COUNT(*)
    FROM regulatory_provisions
    WHERE is_current = true AND source_council = 'ashfield'
    GROUP BY section_header
    ORDER BY section_header
""")
for r in cur.fetchall():
    has_subsection = "---" in r[0] or "Application" in r[0] or "Purpose" in r[0] or "Criteria" in r[0]
    marker = " <-- subsection" if has_subsection else ""
    print(f"  {r[0]}{marker}")

# Signage topic check: are these really signage?
print("\n=== SIGNAGE TOPIC SAMPLE (Leichhardt) ===")
cur.execute("""
    SELECT id, LEFT(provision_text, 150) as snippet
    FROM regulatory_provisions
    WHERE is_current = true AND source_council = 'leichhardt'
      AND v2_topic = 'signage'
    ORDER BY random()
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"  ID {r[0]}: {r[1]}")
    print()

cur.close()
conn.close()
