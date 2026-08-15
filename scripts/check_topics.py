#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print('Topic distribution (Leichhardt actionable provisions):')
cur.execute('''
    SELECT v2_topic, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    GROUP BY v2_topic
    ORDER BY COUNT(*) DESC
''')
total = 0
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')
    total += r[1]
print(f'\nTotal: {total}')

cur.close()
conn.close()
