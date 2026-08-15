#!/usr/bin/env python3
"""Apply topic classifications from backup file in batches."""

import json
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

BACKUP_FILE = 'scripts/backups/verified_classify_20251210_072549.json'
BATCH_SIZE = 100

def get_connection():
    return psycopg2.connect(os.getenv('SUPABASE_DB_URL'))

def main():
    # Load backup
    with open(BACKUP_FILE, 'r') as f:
        updates = json.load(f)

    print(f"Loaded {len(updates)} classifications from backup")

    # Filter to only those that need updating (new_topic != old_topic)
    to_update = [u for u in updates if u['new_topic'] != u['old_topic']]
    print(f"Need to update {len(to_update)} provisions (topic changed)")

    # Apply in batches
    applied = 0
    failed = 0

    for i in range(0, len(to_update), BATCH_SIZE):
        batch = to_update[i:i+BATCH_SIZE]

        try:
            conn = get_connection()
            cur = conn.cursor()

            for item in batch:
                try:
                    cur.execute("""
                        UPDATE regulatory_provisions
                        SET v2_topic = %s
                        WHERE id = %s
                    """, (item['new_topic'], item['provision_id']))
                    applied += 1
                except Exception as e:
                    print(f"  Error on {item['provision_id']}: {e}")
                    failed += 1

            conn.commit()
            cur.close()
            conn.close()

            print(f"Batch {i//BATCH_SIZE + 1}: Applied {len(batch)} updates ({applied} total)")

        except Exception as e:
            print(f"Batch error: {e}")
            failed += len(batch)

    print(f"\nDone! Applied: {applied}, Failed: {failed}")

if __name__ == '__main__':
    main()
