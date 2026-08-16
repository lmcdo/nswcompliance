#!/usr/bin/env python3
import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT lga, dev_type, control_type, value_min, unit, condition, extraction_method, dcp_version
    FROM dcp_setback_controls
    WHERE is_current = TRUE
    ORDER BY lga, dev_type, control_type
""")
rows = cur.fetchall()
print(f'Total rows: {len(rows)}')
print()
cur_lga = None
for r in rows:
    if r['lga'] != cur_lga:
        cur_lga = r['lga']
        print(f'--- {cur_lga} ---')
    cond = (r['condition'] or '')[:60]
    print(f'  {(r["dev_type"] or ""):20} {(r["control_type"] or ""):25} {str(r["value_min"] or ""):>6} {(r["unit"] or ""):3} {(r["extraction_method"] or ""):15} {(r["dcp_version"] or "")} {cond}')
conn.close()
