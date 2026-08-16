#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT lga, count(*) as n
    FROM dcp_setback_controls
    WHERE control_type = 'car_parking' AND is_current = TRUE
    GROUP BY lga ORDER BY lga
""")
total = 0
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]:>4} rows")
    total += r[1]
print(f"\n  {'TOTAL':30s} {total:>4} rows across {cur.rowcount} LGAs")
conn.close()
