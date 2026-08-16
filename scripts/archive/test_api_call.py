#!/usr/bin/env python3
"""Simulate the API call to see what's being returned."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Simulate the precinct layer query WITH precinct_id filter
precinct_id = 'C2.2.3.5'
print(f"Query with precinct_id = '{precinct_id}':")
cur.execute('''
    SELECT id, v2_dcp_part, v2_precinct_id, v2_topic, LEFT(provision_text, 60)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_dcp_layer = 'precinct'
    AND document_id ILIKE '%Leichhardt%'
    AND v2_precinct_id = %s
    LIMIT 10
''', (precinct_id,))

results = cur.fetchall()
print(f"  Found {len(results)} provisions")
for r in results:
    print(f"    ID {r[0]}: {r[1]} [{r[2]}] {r[3]}: {r[4]}...")

# Now query WITHOUT precinct_id filter (what happens if precinct_id not passed)
print(f"\n\nQuery WITHOUT precinct_id filter:")
cur.execute('''
    SELECT id, v2_dcp_part, v2_precinct_id, v2_topic, LEFT(provision_text, 60)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_dcp_layer = 'precinct'
    AND document_id ILIKE '%Leichhardt%'
    LIMIT 20
''')

results = cur.fetchall()
print(f"  Found {len(results)} provisions (showing first 20)")
for r in results:
    print(f"    ID {r[0]}: {r[1]} [{r[2]}] {r[3]}: {r[4]}...")

cur.close()
conn.close()
