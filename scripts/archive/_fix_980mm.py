#!/usr/bin/env python3
"""Fix provision 88235 where source text has '980m' (LaTeX artifact, should be 980mm = 0.98m)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Read current rules
cur.execute("SELECT v2_extracted_rules FROM regulatory_provisions WHERE id = 88235")
row = cur.fetchone()
rules = row[0] if isinstance(row[0], list) else (json.loads(row[0]) if row[0] else [])

# Fix: 980m -> 0.98m (was 980mm in original PDF)
for rule in rules:
    if rule.get('value_exact') == 980.0 and rule.get('unit') == 'm':
        rule['value_exact'] = 0.98
        rule['raw_match'] = 'minimum 980mm (corrected from LaTeX artifact)'
        print(f"Fixed: 980m -> 0.98m")

# Update DB
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_extracted_rules = %s,
        v2_extraction_status = 'complete'
    WHERE id = 88235
""", (json.dumps(rules),))
conn.commit()
print("Provision 88235 updated.")

cur.close()
conn.close()
