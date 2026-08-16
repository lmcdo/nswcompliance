#!/usr/bin/env python3
"""Sample failures to understand what they are."""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

# Load failed IDs
with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
    failed_ids = json.load(f)

# Get samples by topic
cur.execute('''
    SELECT id, v2_topic, LEFT(provision_text, 400) as text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    ORDER BY v2_topic, id
''', (failed_ids,))

by_topic = {}
for row in cur.fetchall():
    topic = row['v2_topic']
    if topic not in by_topic:
        by_topic[topic] = []
    if len(by_topic[topic]) < 3:
        by_topic[topic].append(row)

print("SAMPLE FAILURES BY TOPIC")
print("=" * 70)

for topic in ['heritage', 'building_form', 'site_analysis', 'energy']:
    if topic in by_topic:
        print(f"\n{topic.upper()}:")
        for row in by_topic[topic]:
            text = row['text'][:200].replace('\n', ' ')
            print(f"  ID {row['id']}: {text}...")

cur.close()
conn.close()
