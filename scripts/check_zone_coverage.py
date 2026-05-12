#!/usr/bin/env python3
"""Check lep_zone_coverage and lep_land_use_table stats."""
import psycopg2
from dotenv import load_dotenv
import os
load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=== lep_zone_coverage ===")
cur.execute("SELECT zone, lga, is_complete FROM lep_zone_coverage ORDER BY lga, zone")
for row in cur.fetchall():
    print(f"  {row[0]:6s}  {row[1]:25s}  complete={row[2]}")

print("\n=== lep_land_use_table (counts by LGA) ===")
cur.execute("SELECT lga, COUNT(*) FROM lep_land_use_table GROUP BY lga ORDER BY lga")
for row in cur.fetchall():
    print(f"  {row[0]:25s}  {row[1]:>4} entries")

print("\n=== lep_land_use_table sample for R2 ===")
cur.execute("""
    SELECT lga, development_type, permissibility
    FROM lep_land_use_table
    WHERE zone = 'R2'
    ORDER BY lga, permissibility, development_type
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"  {row[0]:25s}  {row[1]:35s}  {row[2]}")

conn.close()
