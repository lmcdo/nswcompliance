#!/usr/bin/env python3
import sys, os, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Show source_text for suspicious rows before deleting
cur.execute("""
    SELECT id, lga, dev_type, control_type, value_min, value_max, unit, source_text
    FROM dcp_setback_controls
    WHERE (lga='liverpool' AND control_type='max_height')
       OR (lga='blacktown' AND control_type='side_setback' AND value_min >= 5.0)
    ORDER BY lga, control_type
""")
rows = cur.fetchall()
print('Rows to review:')
for r in rows:
    print(f'\n  [{r["id"]}] {r["lga"]} {r["dev_type"]} {r["control_type"]} min={r["value_min"]} max={r["value_max"]} unit={r["unit"]}')
    print(f'  TEXT: {(r["source_text"] or "")[:250]}')

print('\nDeleting...')
cur.execute("""
    DELETE FROM dcp_setback_controls
    WHERE (lga='liverpool' AND control_type='max_height')
       OR (lga='blacktown' AND control_type='side_setback' AND value_min >= 5.0)
""")
print(f'Deleted {cur.rowcount} rows')
conn.commit()
conn.close()
