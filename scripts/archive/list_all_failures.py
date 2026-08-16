#!/usr/bin/env python3
"""List all failures for manual classification."""
import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
    failed_ids = json.load(f)

cur.execute('''
    SELECT id, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    ORDER BY v2_topic, id
''', (failed_ids,))

current_topic = None
for row in cur.fetchall():
    if row['v2_topic'] != current_topic:
        current_topic = row['v2_topic']
        print(f"\n{'='*70}")
        print(f"{current_topic.upper()}")
        print('='*70)

    text = (row['provision_text'] or '')[:250].replace('\n', ' ')
    print(f"\nID {row['id']}:")
    print(f"  {text}...")

cur.close()
conn.close()
