import sys; sys.stdout.reconfigure(encoding='utf-8')
import os, psycopg2
from dotenv import load_dotenv; load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
cur.execute("SELECT id, dev_type, control_type, value_min, is_current, dcp_version, extraction_method FROM dcp_setback_controls WHERE lga='marrickville' ORDER BY dev_type, control_type, id")
for r in cur.fetchall():
    print(f"  id={r[0]} {r[1]:20} {r[2]:30} val={r[3]}  is_current={r[4]}  ver={r[5]}  method={r[6]}")
conn.close()
