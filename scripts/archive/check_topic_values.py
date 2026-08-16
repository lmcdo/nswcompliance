#!/usr/bin/env python3
"""Check all unique topic values in database."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute('''
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
    GROUP BY v2_topic
    ORDER BY cnt DESC
''')

print("Topic values in database:")
for row in cur.fetchall():
    print(f'{row[1]:5}  {row[0]}')

cur.close()
conn.close()
