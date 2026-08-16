#!/usr/bin/env python3
"""Add v2_extracted_rules and v2_extraction_status columns to regulatory_provisions."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Add columns (IF NOT EXISTS prevents errors if re-run)
cur.execute("""
    ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS v2_extracted_rules jsonb,
    ADD COLUMN IF NOT EXISTS v2_extraction_status text
""")
conn.commit()

# Verify
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    AND column_name IN ('v2_extracted_rules', 'v2_extraction_status')
    ORDER BY column_name
""")
rows = cur.fetchall()
print("Columns after migration:")
for r in rows:
    print(f"  {r[0]}: {r[1]}")

cur.close()
conn.close()
print("\nDone.")
