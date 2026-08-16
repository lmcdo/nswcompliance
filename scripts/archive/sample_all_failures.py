#!/usr/bin/env python3
"""Sample failures from each topic category."""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
    failed_ids = json.load(f)

cur.execute('''
    SELECT id, v2_topic, LEFT(provision_text, 350) as text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    ORDER BY v2_topic, id
''', (failed_ids,))

by_topic = defaultdict(list)
for row in cur.fetchall():
    by_topic[row['v2_topic']].append(row)

# Show 5 samples from top failing topics
for topic in ['heritage', 'building_form', 'site_analysis', 'contamination', 'roofing', 'landscaping', 'trees', 'parking', 'energy']:
    if topic in by_topic:
        print(f"\n{'='*70}")
        print(f"{topic.upper()} ({len(by_topic[topic])} failures)")
        print('='*70)
        for row in by_topic[topic][:5]:
            text = row['text'].replace('\n', ' ')[:250]
            print(f"\nID {row['id']}:\n  {text}...")

cur.close()
conn.close()
