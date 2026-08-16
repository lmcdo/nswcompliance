#!/usr/bin/env python3
"""Check if v2_extracted_rules and v2_extraction_status columns exist."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    AND column_name IN ('v2_extracted_rules', 'v2_extraction_status')
    ORDER BY column_name
""")
rows = cur.fetchall()
if rows:
    print("Columns already exist:")
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
else:
    print("NONE - columns need to be created")
cur.close()
conn.close()
