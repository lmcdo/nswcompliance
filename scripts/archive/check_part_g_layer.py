#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("Part G provision layers:")
cur.execute('''
    SELECT v2_dcp_layer, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_is_actionable = true
    GROUP BY v2_dcp_layer
''')
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print("\n\nPart G provisions with v2_precinct_id:")
cur.execute('''
    SELECT v2_precinct_id, v2_dcp_layer, COUNT(*)
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part G'
    AND v2_is_actionable = true
    GROUP BY v2_precinct_id, v2_dcp_layer
    ORDER BY v2_precinct_id
''')
for r in cur.fetchall():
    print(f"  {r[0]} [{r[1]}]: {r[2]}")

cur.close()
conn.close()
