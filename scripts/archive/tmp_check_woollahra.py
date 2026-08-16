import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'dcp_setback_controls' ORDER BY ordinal_position")
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]}")
conn.close()
