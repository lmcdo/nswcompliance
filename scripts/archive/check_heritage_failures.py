#!/usr/bin/env python3
"""Check heritage failures to understand the pattern."""
import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
    failed_ids = json.load(f)

cur.execute('''
    SELECT id, v2_topic, LEFT(provision_text, 400) as text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    AND v2_topic = 'heritage'
    ORDER BY id
    LIMIT 20
''', (failed_ids,))

print("HERITAGE FAILURES (20 samples):")
print("=" * 70)
for row in cur.fetchall():
    text = row['text'].replace('\n', ' ')[:300]
    print(f"\nID {row['id']}:")
    print(f"  {text}...")

cur.close()
conn.close()
