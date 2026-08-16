import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
for lga in ['marrickville', 'leichhardt', 'ashfield', 'blacktown', 'waverley', 'canterbury_bankstown']:
    cur.execute(
        "SELECT dev_type, control_type, value_min, value_max, condition FROM dcp_setback_controls WHERE lga=%s AND is_current=TRUE ORDER BY dev_type, control_type",
        (lga,)
    )
    rows = cur.fetchall()
    print(f"\n{lga}: {len(rows)} rows")
    for r in rows:
        print(f"  {r[0]:20} {r[1]:20} min={r[2]} max={r[3]}  cond={r[4]}")
conn.close()
