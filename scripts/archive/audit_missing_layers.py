#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit Marrickville provisions missing layer attribution
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load .env file
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("MARRICKVILLE PROVISIONS MISSING LAYER ATTRIBUTION")
print("=" * 80)

# Count total missing
cursor.execute("""
SELECT COUNT(*) as missing
FROM regulatory_provisions
WHERE source_council = 'marrickville'
  AND v2_provision_type = 'control'
  AND v2_heritage_type IS DISTINCT FROM 'descriptive'
  AND v2_dcp_layer IS NULL
""")
missing_total = cursor.fetchone()['missing']
print(f"\nTotal provisions missing v2_dcp_layer: {missing_total}\n")

# Breakdown by topic
cursor.execute("""
SELECT v2_topic, COUNT(*) as cnt
FROM regulatory_provisions
WHERE source_council = 'marrickville'
  AND v2_provision_type = 'control'
  AND v2_heritage_type IS DISTINCT FROM 'descriptive'
  AND v2_dcp_layer IS NULL
GROUP BY v2_topic
ORDER BY cnt DESC
""")

print("By topic:")
for row in cursor.fetchall():
    print(f"  {row['v2_topic']:<20} {row['cnt']:>4} provisions")

# Sample provisions
print("\nSample provisions without layer (first 5):")
cursor.execute("""
SELECT
  id,
  v2_dcp_part,
  source_chapter_key,
  v2_topic,
  SUBSTRING(provision_text, 1, 80) as text_sample
FROM regulatory_provisions
WHERE source_council = 'marrickville'
  AND v2_provision_type = 'control'
  AND v2_heritage_type IS DISTINCT FROM 'descriptive'
  AND v2_dcp_layer IS NULL
LIMIT 5
""")

for row in cursor.fetchall():
    print(f"\nID {row['id']}: {row['v2_dcp_part'] or row['source_chapter_key']}")
    print(f"  Topic: {row['v2_topic']}")
    print(f"  Text: {row['text_sample']}...")

# Check what layer they should have
print("\n\nANALYSIS:")
print("These provisions are missing v2_dcp_layer attribution.")
print("Since they're controls (not objectives/descriptives), they should apply")
print("to all properties, so they should be tagged as v2_dcp_layer='generic'")

cursor.close()
conn.close()
