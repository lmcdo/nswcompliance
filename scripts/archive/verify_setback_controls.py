#!/usr/bin/env python3
import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT lga, dev_type, control_type, value_min, value_max, unit,
           applicability, section_ref
    FROM dcp_setback_controls
    ORDER BY lga, control_type
""")
rows = cur.fetchall()
print(f"Total rows: {len(rows)}")
for r in rows:
    print(f"  {r['lga']:20} | {r['control_type']:28} | min={r['value_min']} max={r['value_max']} {r['unit']} | {r['applicability']} | {r['section_ref']}")
conn.close()
