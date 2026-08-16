#!/usr/bin/env python3
"""Normalize all topic names to lowercase snake_case."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Mapping from current values to normalized values
TOPIC_MAPPING = {
    'Height': 'height',
    'Setbacks': 'setbacks',
    'Parking': 'parking',
    'Landscaping': 'landscaping',
    'Access': 'access',
    'Building Form': 'building_form',
    'Signage': 'signage',
    'Heritage': 'heritage',
    'Fencing': 'fencing',
    'Trees': 'trees',
    'Privacy': 'privacy',
    'Stormwater': 'stormwater',
    'Waste': 'waste',
    'Flooding': 'flooding',
    'Open Space': 'open_space',
    'Safety': 'safety',
    'Contamination': 'contamination',
    'Solar': 'solar',
    'urban_design': 'building_design',  # Map to existing topic
    'food_premises': 'general',  # food premises controls go to general
}

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

print("Topic normalization plan:")
total = 0
for old_topic, new_topic in TOPIC_MAPPING.items():
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_topic = %s AND v2_is_actionable = true
    """, (old_topic,))
    count = cur.fetchone()[0]
    if count > 0:
        print(f"  {old_topic} -> {new_topic}: {count}")
        total += count

print(f"\nTotal to update: {total}")

if args.execute:
    print("\nApplying changes...")
    for old_topic, new_topic in TOPIC_MAPPING.items():
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_topic = %s
            WHERE v2_topic = %s
        """, (new_topic, old_topic))
        if cur.rowcount > 0:
            print(f"  Updated {cur.rowcount} rows: {old_topic} -> {new_topic}")

    conn.commit()
    print("Done!")

cur.close()
conn.close()
