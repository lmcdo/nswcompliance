#!/usr/bin/env python3
"""Fix ALL Leichhardt duplicates across all topics."""
import os
import psycopg2
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find all Leichhardt provisions
cur.execute('''
    SELECT id, v2_dcp_part, v2_topic, pdf_page, LEFT(provision_text, 150) as text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    AND v2_is_actionable = true
    ORDER BY provision_text, pdf_page, id
''')

rows = cur.fetchall()
print(f"Total Leichhardt provisions: {len(rows)}")

# Group by text (first 150 chars) to find duplicates
by_text = defaultdict(list)
for r in rows:
    by_text[r[4]].append((r[0], r[1], r[2], r[3]))  # id, part, topic, page

duplicates_to_remove = []

for text, entries in by_text.items():
    if len(entries) > 1:
        # Sort: prefer ones with page numbers, then lowest ID
        sorted_entries = sorted(entries, key=lambda x: (x[3] is None, x[0]))
        keep = sorted_entries[0]
        for entry in sorted_entries[1:]:
            duplicates_to_remove.append(entry[0])

print(f"Duplicates to remove: {len(duplicates_to_remove)}")

# Show sample
print("\nSample duplicates:")
sample_shown = 0
for text, entries in by_text.items():
    if len(entries) > 1 and sample_shown < 5:
        print(f"  '{text[:60]}...' has {len(entries)} copies")
        sample_shown += 1

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute and duplicates_to_remove:
    cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = ANY(%s)", (duplicates_to_remove,))
    conn.commit()
    print(f"\nDone! Marked {cur.rowcount} duplicates as not actionable")

cur.close()
conn.close()
