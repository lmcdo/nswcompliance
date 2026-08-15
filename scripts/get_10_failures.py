#!/usr/bin/env python3
"""Get 10 failed provisions for manual review."""
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

# Get 10 diverse samples
cur.execute('''
    SELECT id, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    ORDER BY v2_topic, id
    LIMIT 10
''', (failed_ids[:100],))

for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n{'='*70}")
    print(f"PROVISION {i}")
    print(f"{'='*70}")
    print(f"ID: {row['id']}")
    print(f"CURRENT TOPIC: {row['v2_topic']}")
    print(f"TEXT:\n{row['provision_text'][:600]}")

cur.close()
conn.close()
