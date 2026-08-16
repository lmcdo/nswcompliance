#!/usr/bin/env python3
"""Normalize ALL topic names to lowercase snake_case."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Get all distinct topics
cur.execute('''
    SELECT DISTINCT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_topic IS NOT NULL
    GROUP BY v2_topic
    ORDER BY v2_topic
''')

print("Current topics:")
topics = {}
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")
    topics[r[0]] = r[1]

# Mapping - title case / spaces to snake_case
TOPIC_MAPPING = {
    'Building Form & Character': 'building_form',
    'Access & Movement': 'access',
    'Height & Envelope': 'height',
    'Open Space': 'open_space',
    'Parking': 'parking',
    'Landscaping': 'landscaping',
    'Setbacks': 'setbacks',
    'Heritage': 'heritage',
    'Signage': 'signage',
    'Privacy': 'privacy',
    'Site Analysis': 'site_analysis',
    'Waste Management': 'waste',
    'General': 'general',
    'Solar Access': 'solar',
    'Site Contamination': 'contamination',
    'Safety & Security': 'safety',
    'Stormwater': 'stormwater',
    'Trees & Vegetation': 'trees',
    'Sustainability': 'sustainability',
    'Views': 'views',
    'Fencing': 'fencing',
    'Flooding': 'flooding',
}

print("\nNormalization plan:")
total = 0
for old, new in TOPIC_MAPPING.items():
    if old in topics:
        print(f"  {old} -> {new}: {topics[old]}")
        total += topics[old]

print(f"\nTotal to update: {total}")

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

if args.execute:
    print("\nApplying...")
    for old, new in TOPIC_MAPPING.items():
        cur.execute("UPDATE regulatory_provisions SET v2_topic = %s WHERE v2_topic = %s", (new, old))
        if cur.rowcount > 0:
            print(f"  {old} -> {new}: {cur.rowcount}")
    conn.commit()
    print("Done!")

cur.close()
conn.close()
