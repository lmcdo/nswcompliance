#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check Part C Section 2 provisions
print("Part C Section 2 provisions:")
cur.execute('''
    SELECT DISTINCT v2_precinct_id, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part C Section 2'
    AND v2_is_actionable = true
    GROUP BY v2_precinct_id
    ORDER BY v2_precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Check what precinct_ids exist for Leichhardt precinct layer
print("\n\nLeichhardt precinct layer precinct_ids:")
cur.execute('''
    SELECT DISTINCT v2_precinct_id, v2_dcp_part, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'precinct'
    AND document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    GROUP BY v2_precinct_id, v2_dcp_part
    ORDER BY v2_precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]}): {r[2]}")

cur.close()
conn.close()
