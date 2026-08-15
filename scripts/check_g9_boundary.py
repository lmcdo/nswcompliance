#!/usr/bin/env python3
"""Check if G9 boundary exists and covers Norton St."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check what Leichhardt precincts exist in boundaries table
print("Leichhardt precinct boundaries:")
cur.execute('''
    SELECT precinct_id, precinct_name, former_council
    FROM dcp_precinct_boundaries
    WHERE former_council = 'Leichhardt'
    OR precinct_id LIKE 'G%'
    ORDER BY precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]} ({r[2]})")

# Check if G9 exists
print("\n\nG9 boundary check:")
cur.execute('''
    SELECT precinct_id, precinct_name, ST_AsText(ST_Centroid(boundary))
    FROM dcp_precinct_boundaries
    WHERE precinct_id = 'G9'
''')
g9 = cur.fetchone()
if g9:
    print(f"  G9 exists: {g9[1]}, centroid: {g9[2]}")
else:
    print("  G9 NOT FOUND!")

# What precinct does 70 Norton St fall into?
# Norton St, Leichhardt approx coords: -33.882, 151.157
print("\n\nPrecinct detection for 70 Norton St (approx coords -33.882, 151.157):")
cur.execute('''
    SELECT precinct_id, precinct_name, former_council
    FROM dcp_precinct_boundaries
    WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint(151.157, -33.882), 4326))
''')
result = cur.fetchall()
if result:
    for r in result:
        print(f"  Detected: {r[0]} - {r[1]} ({r[2]})")
else:
    print("  No precinct detected for these coordinates!")

# What are ALL precincts that contain "Norton" in name or provisions?
print("\n\nPrecincts mentioning Norton Street:")
cur.execute('''
    SELECT DISTINCT v2_precinct_id
    FROM regulatory_provisions
    WHERE provision_text ILIKE '%norton street%'
    AND v2_is_actionable = true
''')
for r in cur.fetchall():
    print(f"  {r[0]}")

cur.close()
conn.close()
