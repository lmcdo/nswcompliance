import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

# Chapter registry
print("=== chapter registry ===")
cur.execute("""
    SELECT council, chapter_key, council_url, r2_current_path
    FROM dcp_chapter_registry
    WHERE council IN ('marrickville','leichhardt','ashfield')
      AND is_active = TRUE
    ORDER BY council, chapter_key
""")
for r in cur.fetchall():
    print(f"  {r[0]} / {r[1]}")
    print(f"    url: {r[2]}")
    print(f"    r2:  {r[3]}")

# dcp_general_requirements — existing setback data
print("\n=== dcp_general_requirements (setbacks) ===")
cur.execute("""
    SELECT former_council, category, subcategory, control_type,
           value_numeric, unit, conditional_text, section_reference
    FROM dcp_general_requirements
    WHERE former_council IN ('Marrickville','Leichhardt','Ashfield')
      AND category IN ('setback_front','setback_side','setback_rear','setbacks')
      AND evidence_type = 'manual'
    ORDER BY former_council, category, subcategory
""")
for r in cur.fetchall():
    print(f"  {r[0]:15} {r[1]:18} {r[2]:25} ct={r[3]} val={r[4]} {r[5]}  cond={r[6]}  ref={r[7]}")

conn.close()
