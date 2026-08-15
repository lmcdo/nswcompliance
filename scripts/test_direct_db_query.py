"""Test direct database query to check if enrichment data is causing issues."""

import os, psycopg2, time
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT'),
    connect_timeout=5
)
cur = conn.cursor()

print('Testing simple precinct query...')
start = time.time()

cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
      AND (v2_precinct_id = '47_' OR v2_precinct_id = 'PART_G_OVERVIEW');
""")

count = cur.fetchone()[0]
elapsed = time.time() - start

print(f'Query completed in {elapsed:.2f}s')
print(f'Result: {count} provisions')

# Test more complex query like the API would do
print('\nTesting full API-style query...')
start = time.time()

cur.execute("""
    SELECT id, provision_text
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
      AND regulatory_provisions.is_current = TRUE
      AND document_id ILIKE '%Marrickville%'
      AND (v2_precinct_id = '47_' OR v2_precinct_id = 'PART_G_OVERVIEW')
    LIMIT 10;
""")

provisions = cur.fetchall()
elapsed = time.time() - start

print(f'Query completed in {elapsed:.2f}s')
print(f'Result: {len(provisions)} provisions (limited to 10)')
for id, text in provisions[:3]:
    print(f'  ID {id}: {text[:80]}...')

cur.close()
conn.close()
print('\nDatabase queries working correctly!')
