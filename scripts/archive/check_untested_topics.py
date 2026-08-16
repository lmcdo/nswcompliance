#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# All topics with keyword tests
tested_topics = ['setbacks', 'parking', 'height', 'heritage', 'landscaping', 'privacy', 'solar', 'trees',
              'stormwater', 'flooding', 'fencing', 'access', 'building_design', 'building_form',
              'signage', 'vehicle_access', 'bicycle_parking', 'roofing', 'open_space', 'site_analysis',
              'water', 'energy', 'contamination', 'waste', 'safety', 'wsud', 'views',
              'general', 'precinct', 'site_specific', 'biodiversity', 'environmental', 'social_impact', 'sustainability']

cur.execute('''
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_topic IS NOT NULL
    AND v2_topic NOT IN %s
    GROUP BY v2_topic
    ORDER BY cnt DESC
''', (tuple(tested_topics),))

print('Topics without keyword tests:')
total = 0
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')
    total += row[1]
print(f'Total: {total}')

cur.close()
conn.close()
