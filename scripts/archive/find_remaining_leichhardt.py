"""Find the 1 remaining Leichhardt provision."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    port=os.getenv('PGPORT')
)
cur = conn.cursor()

cur.execute("""
    SELECT id, document_id, provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_dcp_layer = 'precinct'
      AND v2_is_actionable = true
      AND v2_precinct_id IS NULL
    LIMIT 5;
""")

print('Remaining Leichhardt provisions:')
for id, doc_id, text in cur.fetchall():
    print(f'\nID: {id}')
    print(f'Document: {doc_id}')
    print(f'Text: {text[:300]}...')

cur.close()
conn.close()
