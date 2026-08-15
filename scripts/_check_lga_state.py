import sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')
import os, psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("""
  SELECT council, chapter_key, needs_extraction, is_active, r2_current_path IS NOT NULL as has_r2
  FROM dcp_chapter_registry
  WHERE council IN ('waverley', 'woollahra')
  ORDER BY council, sort_order
""")
rows = cur.fetchall()
print('Registry:')
for r in rows:
    print(' ', r)

# Provision counts using document_id pattern
cur.execute("""
  SELECT
    CASE WHEN document_id ILIKE '%waverley%' THEN 'waverley'
         WHEN document_id ILIKE '%woollahra%' THEN 'woollahra' END as council,
    count(*) as n,
    count(*) filter (where is_canonical = true) as canonical
  FROM regulatory_provisions
  WHERE document_id ILIKE '%waverley%' OR document_id ILIKE '%woollahra%'
  GROUP BY 1
""")
print('\nProvision counts:')
for r in cur.fetchall():
    print(' ', r)

conn.close()
