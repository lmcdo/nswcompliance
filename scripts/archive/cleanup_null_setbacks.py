#!/usr/bin/env python3
import sys, os, psycopg2
sys.stdout.reconfigure(encoding='utf-8')
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
cur.execute("DELETE FROM dcp_setback_controls WHERE value_min IS NULL AND value_max IS NULL")
print(f'Deleted {cur.rowcount} null-value rows')
cur.execute("SELECT lga, dev_type, control_type, value_min, unit FROM dcp_setback_controls WHERE is_current=TRUE ORDER BY lga, dev_type, control_type")
rows = cur.fetchall()
print(f'Total remaining: {len(rows)}')
cur_lga = None
for r in rows:
    if r[0] != cur_lga:
        cur_lga = r[0]
        print(f'  --- {cur_lga} ---')
    print(f'    {(r[1] or ""):20} {(r[2] or ""):25} {str(r[3] or ""):>6} {r[4] or ""}')
conn.commit()
conn.close()
