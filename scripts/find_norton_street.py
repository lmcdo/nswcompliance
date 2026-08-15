#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find precinct IDs for Norton Street
print("Searching for Norton Street precincts...")
cur.execute('''
    SELECT DISTINCT precinct_id, precinct_name
    FROM dcp_precinct_provisions
    WHERE precinct_name ILIKE '%norton%'
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\nSearching in regulatory_provisions for Norton Street...")
cur.execute('''
    SELECT DISTINCT v2_precinct_id
    FROM regulatory_provisions
    WHERE v2_precinct_id ILIKE '%norton%'
''')
for r in cur.fetchall():
    print(f"  {r[0]}")

print("\nPart G precincts...")
cur.execute('''
    SELECT DISTINCT v2_precinct_id, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_precinct_id IS NOT NULL
    GROUP BY v2_precinct_id
    ORDER BY v2_precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} provisions")

cur.close()
conn.close()
