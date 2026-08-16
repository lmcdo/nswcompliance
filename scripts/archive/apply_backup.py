#!/usr/bin/env python3
"""Apply changes from backup file."""
import os
import sys
import json

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

import psycopg2

backup_file = sys.argv[1] if len(sys.argv) > 1 else 'scripts/backups/phase2_llm_20251209_233009.json'

with open(backup_file, 'r') as f:
    data = json.load(f)

changes = data.get('changes', [])
not_actionable = data.get('not_actionable', [])

print(f"Changes to apply: {len(changes)}")
print(f"Not actionable to mark: {len(not_actionable)}")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Apply in batches to avoid timeout
batch_size = 100

print("\nApplying topic changes...")
for i in range(0, len(changes), batch_size):
    batch = changes[i:i+batch_size]
    for prov_id, old_topic, new_topic in batch:
        cur.execute(
            "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
            (new_topic, prov_id)
        )
    conn.commit()
    print(f"  Applied {min(i+batch_size, len(changes))}/{len(changes)}")

print("\nMarking not actionable...")
for i in range(0, len(not_actionable), batch_size):
    batch = not_actionable[i:i+batch_size]
    for prov_id in batch:
        cur.execute(
            "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
            (prov_id,)
        )
    conn.commit()
    print(f"  Applied {min(i+batch_size, len(not_actionable))}/{len(not_actionable)}")

cur.close()
conn.close()

print("\nDone!")
print(f"Applied {len(changes)} topic changes")
print(f"Marked {len(not_actionable)} as not actionable")
