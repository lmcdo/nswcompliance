#!/usr/bin/env python3
"""Fix Part E duplicates and remaining TOC entries."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find all Part E water provisions
cur.execute('''
    SELECT id, pdf_page, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE v2_dcp_part = 'Part E'
    AND v2_topic = 'water'
    AND v2_is_actionable = true
    ORDER BY provision_text, pdf_page, id
''')

rows = cur.fetchall()
print(f"Total Part E water provisions: {len(rows)}")

# Group by text to find duplicates
from collections import defaultdict
by_text = defaultdict(list)
for r in rows:
    by_text[r[2]].append((r[0], r[1]))

duplicates_to_remove = []
toc_to_remove = []

for text, ids in by_text.items():
    # Check for TOC pattern
    if '. .' in text or '.. .' in text:
        for id, page in ids:
            toc_to_remove.append(id)
        continue

    # If more than one, keep only the first (with page number if possible)
    if len(ids) > 1:
        # Sort: prefer ones with page numbers
        sorted_ids = sorted(ids, key=lambda x: (x[1] is None, x[0]))
        keep = sorted_ids[0]
        for id, page in sorted_ids[1:]:
            duplicates_to_remove.append(id)
            print(f"Duplicate: ID {id} (page {page}) - keeping ID {keep[0]}")

print(f"\nTOC entries to remove: {len(toc_to_remove)}")
print(f"Duplicates to remove: {len(duplicates_to_remove)}")

all_to_remove = list(set(toc_to_remove + duplicates_to_remove))
print(f"Total to mark not actionable: {len(all_to_remove)}")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute and all_to_remove:
    cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = ANY(%s)", (all_to_remove,))
    conn.commit()
    print(f"Done! Updated {cur.rowcount} rows")

cur.close()
conn.close()
