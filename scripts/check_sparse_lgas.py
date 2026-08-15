#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
for lga in ['hornsby', 'northern_beaches', 'blacktown', 'campbelltown', 'liverpool']:
    cur.execute(
        'SELECT dev_type, control_type, value_min, value_max, unit, condition '
        'FROM dcp_setback_controls WHERE lga=%s AND is_current=TRUE ORDER BY dev_type, control_type',
        (lga,)
    )
    rows = cur.fetchall()
    print(f'{lga} ({len(rows)} rows):')
    for r in rows:
        print(f'  {r[0]:20} {r[1]:18} min={r[2]} max={r[3]} {r[4]}  [{(r[5] or "")[:55]}]')
conn.close()
