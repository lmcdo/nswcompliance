#!/usr/bin/env python3
"""Classify and fix the remaining 164 provisions."""
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
    SELECT id, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
''', (failed_ids,))

provisions = cur.fetchall()

# Patterns for NOT_ACTIONABLE
not_actionable_patterns = [
    'in using this guideline reference should also be made',
    'this guideline applies to the inner west',
    'reference should also be made to section',
    'this sub area can be described',
    'civic centre of leichhardt',
    'the two principle sources of technical information',
    'note: universal design ensures',
    'also, many apartments offered for sale',
]

# Patterns for topic changes
topic_changes = {
    'rock features': 'landscaping',  # environmental about rock features -> landscaping
    'new allotments shall be consistent': 'general',  # subdivision control
    'site and context analysis': 'site_analysis',
    'heating systems using gas': 'energy',
    'loading and unloading facilities': 'vehicle_access',
    'ensure the efficient design of the turning bays': 'vehicle_access',
    'continuous deflective separators': 'stormwater',
    'usable balcony area': 'access',  # accessibility
}

not_actionable = []
changes = []
keep = []

for prov in provisions:
    text = (prov['provision_text'] or '')[:500].lower()
    topic = prov['v2_topic']
    pid = prov['id']

    # Check for NOT_ACTIONABLE
    is_not_actionable = any(p in text for p in not_actionable_patterns)
    if is_not_actionable:
        not_actionable.append((pid, topic))
        continue

    # Check for topic changes
    changed = False
    for pattern, new_topic in topic_changes.items():
        if pattern in text:
            if new_topic != topic:
                changes.append((pid, topic, new_topic, pattern))
            changed = True
            break

    if not changed:
        keep.append((pid, topic, text[:100]))

print(f"NOT_ACTIONABLE: {len(not_actionable)}")
print(f"Topic changes: {len(changes)}")
print(f"Keep (need review): {len(keep)}")

# Sample keep
print("\nSample KEEP (need manual review):")
for pid, topic, text in keep[:10]:
    print(f"  ID {pid} ({topic}): {text}...")

# Apply
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute:
    print("\nApplying...")
    for pid, old_topic in not_actionable:
        cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s", (pid,))

    for pid, old, new, pattern in changes:
        cur.execute("UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s", (new, pid))

    conn.commit()
    print(f"Marked {len(not_actionable)} as NOT_ACTIONABLE")
    print(f"Changed {len(changes)} topics")

cur.close()
conn.close()
