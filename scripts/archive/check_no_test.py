#!/usr/bin/env python3
"""Check what the 'no test' provisions actually contain."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

no_test_topics = ['general', 'precinct', 'site_specific', 'biodiversity', 'environmental', 'social_impact', 'sustainability']

cur.execute('''
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_topic = ANY(%s)
    GROUP BY v2_topic
    ORDER BY cnt DESC
''', (no_test_topics,))

print('NO-TEST TOPICS:')
total = 0
for row in cur.fetchall():
    print(f'  {row["v2_topic"]}: {row["cnt"]}')
    total += row["cnt"]
print(f'  TOTAL: {total}')

# Sample each
print('\n' + '='*60)
for topic in ['general', 'precinct', 'site_specific']:
    cur.execute('''
        SELECT id, LEFT(provision_text, 250) as text
        FROM regulatory_provisions
        WHERE v2_is_actionable = true AND v2_topic = %s
        LIMIT 5
    ''', (topic,))
    print(f'\n{topic.upper()}:')
    for row in cur.fetchall():
        text = (row['text'] or '').replace('\n', ' ')[:200]
        print(f'  ID {row["id"]}: {text}...')

cur.close()
conn.close()
