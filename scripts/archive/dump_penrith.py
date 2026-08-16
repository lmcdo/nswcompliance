#!/usr/bin/env python3
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT zone, zone_name, development_type, permissibility
    FROM lep_land_use_table
    WHERE lga = 'Penrith'
    ORDER BY zone, permissibility, development_type
""")
for row in cur.fetchall():
    print(f"zone: {row[0]:5s} | zone_name: {row[1]:40s} | development_type: {row[2]:55s} | permissibility: {row[3]}")
print(f"\nTotal: {cur.rowcount} rows")
conn.close()
