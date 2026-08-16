#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT lga, dev_type, control_type, value_min, value_max, unit,
           condition, applicability, section_ref
    FROM dcp_setback_controls
    ORDER BY lga, control_type
""")
rows = cur.fetchall()
print(f"Total rows: {len(rows)}\n")
for r in rows:
    print(f"{r['lga']:15} {r['control_type']:30} min={r['value_min']}  max={r['value_max']}  unit={r['unit']}")
    print(f"  cond={r['condition']}")
    print(f"  {r['applicability']}  ref={r['section_ref']}")
    print()
conn.close()
