#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPIC VERIFICATION
Check if provisions actually match their assigned topic
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2
import re

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Keywords that SHOULD appear in each topic
TOPIC_KEYWORDS = {
    'Setbacks': ['setback', 'setbacks', 'set back', 'building line', 'boundary clearance'],
    'Parking': ['parking', 'car space', 'garage', 'carport', 'vehicle parking', 'driveway'],
    'Height': ['height', 'storey', 'storeys', 'floor level', 'building height', 'maximum height'],
    'Heritage': ['heritage', 'conservation', 'historic', 'character', 'hca', 'heritage item'],
    'Landscaping': ['landscap', 'planting', 'garden', 'vegetation', 'green'],
}

print("=" * 80)
print("TOPIC VERIFICATION - Do provisions match their assigned topic?")
print("=" * 80)

for council in ['leichhardt', 'ashfield', 'marrickville']:
    print(f"\n{'='*80}")
    print(f"COUNCIL: {council.upper()}")
    print(f"{'='*80}")

    council_results = []

    for topic, keywords in TOPIC_KEYWORDS.items():
        # Get provisions tagged with this topic
        cur.execute(f'''
            SELECT id, v2_marker, LEFT(provision_text, 300)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{council}%'
            AND v2_is_actionable = true
            AND v2_topic = '{topic}'
            LIMIT 50
        ''')

        rows = cur.fetchall()

        matches = 0
        for row in rows:
            prov_id, marker, text = row
            text_lower = text.lower()
            found = any(kw.lower() in text_lower for kw in keywords)
            if found:
                matches += 1

        total = len(rows)
        match_pct = (matches * 100 // total) if total > 0 else 0
        council_results.append((topic, total, matches, match_pct))

    print(f"\n{'Topic':<15} {'Checked':<10} {'Match':<10} {'Accuracy':<10}")
    print("-" * 45)
    for topic, total, matches, pct in council_results:
        status = "✓" if pct >= 70 else "✗"
        print(f"{topic:<15} {total:<10} {matches:<10} {pct}% {status}")

conn.close()

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("""
If match % is low (< 70%), the topic classification is unreliable.
Provisions are being assigned to topics they don't belong to.

To fix:
1. Re-extract from PDFs with section hierarchy (most reliable)
2. Re-run LLM with section header context
3. Manual review and correction
""")
