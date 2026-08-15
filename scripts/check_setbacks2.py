#!/usr/bin/env python3
import sys, os, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT lga, dev_type, control_type, value_min, value_max, unit, extraction_method
    FROM dcp_setback_controls
    WHERE is_current=TRUE AND (value_min IS NULL OR control_type='max_height')
    ORDER BY lga, dev_type
""")
rows = cur.fetchall()
print(f'max_height / null rows: {len(rows)}')
for r in rows:
    print(f'  {r["lga"]:20} {r["dev_type"]:20} {r["control_type"]:25} min={r["value_min"]} max={r["value_max"]} unit={r["unit"]}')
conn.close()
