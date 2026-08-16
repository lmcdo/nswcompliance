#!/usr/bin/env python3
"""
STEP 5: FIX REMAINING PROVISIONS WITHOUT TOPICS

Handle the 334 provisions that still don't have topics:
1. Leichhardt unknown part -> mark non-actionable (intro text)
2. Leichhardt Part G without topic -> site_specific
3. Ashfield Chapter D -> precinct
4. Marrickville remaining -> by part

Run with --execute to actually make changes.
"""
import os
import sys
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*70)
    print("STEP 5: FIX REMAINING PROVISIONS WITHOUT TOPICS")
    print("="*70)

    if not args.execute:
        print("\n*** DRY RUN ***\n")

    topic_updates = []
    garbage_ids = []

    # Get all provisions without topics
    cur.execute('''
        SELECT id, document_id, v2_dcp_part, LEFT(provision_text, 200)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
        AND (v2_topic IS NULL OR v2_topic = '' OR v2_topic = 'None')
    ''')

    provisions = cur.fetchall()
    print(f"Provisions without topics: {len(provisions)}")

    for prov_id, doc_id, part, text in provisions:
        doc_lower = (doc_id or '').lower()

        # LEICHHARDT
        if 'leichhardt' in doc_lower:
            if part == 'unknown':
                # Intro/admin text - mark non-actionable
                garbage_ids.append(prov_id)
            elif part == 'Part G':
                topic_updates.append((prov_id, 'site_specific'))
            elif part == 'Part C Section 1':
                # Should have been caught by page inheritance - default to general
                topic_updates.append((prov_id, 'general'))
            else:
                topic_updates.append((prov_id, 'general'))

        # ASHFIELD
        elif 'ashfield' in doc_lower:
            if part == 'Chapter D':
                topic_updates.append((prov_id, 'precinct'))
            elif part == 'Chapter E1':
                topic_updates.append((prov_id, 'heritage'))
            elif part == 'unknown':
                garbage_ids.append(prov_id)
            else:
                topic_updates.append((prov_id, 'general'))

        # MARRICKVILLE
        elif 'marrickville' in doc_lower:
            if part == 'Part 8':
                topic_updates.append((prov_id, 'heritage'))
            elif part == 'Part 9':
                topic_updates.append((prov_id, 'precinct'))
            elif part == 'unknown':
                garbage_ids.append(prov_id)
            else:
                topic_updates.append((prov_id, 'general'))

    print(f"\nTopic updates: {len(topic_updates)}")
    print(f"Mark non-actionable: {len(garbage_ids)}")

    # Show breakdown
    topic_counts = {}
    for _, topic in topic_updates:
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    print("\nTopic distribution:")
    for topic, cnt in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {topic}: {cnt}")

    if args.execute:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/step5_remaining_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        backup_data = {
            'topic_updates': topic_updates,
            'garbage_ids': garbage_ids
        }
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        print(f"\nBackup: {backup_file}")

        for prov_id, topic in topic_updates:
            cur.execute("UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s", (topic, prov_id))

        if garbage_ids:
            cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = ANY(%s)", (garbage_ids,))

        conn.commit()
        print(f"Applied {len(topic_updates)} topic updates")
        print(f"Marked {len(garbage_ids)} non-actionable")

    conn.close()


if __name__ == '__main__':
    main()
