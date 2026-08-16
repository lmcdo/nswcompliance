#!/usr/bin/env python3
"""Get all failed provisions for Claude to classify."""
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
    SELECT id, v2_topic, LEFT(provision_text, 500) as text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
    ORDER BY id
''', (failed_ids,))

provisions = cur.fetchall()

# Output as JSON for processing
output = []
for row in provisions:
    output.append({
        'id': row['id'],
        'current_topic': row['v2_topic'],
        'text': row['text']
    })

with open('scripts/checkpoints/failures_to_classify.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Exported {len(output)} provisions to scripts/checkpoints/failures_to_classify.json")

cur.close()
conn.close()
