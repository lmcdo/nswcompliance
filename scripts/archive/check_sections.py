#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DATA RELIABILITY CHECK
Show exactly what's in the database for Leichhardt provisions
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("=" * 80)
print("LEICHHARDT DATA RELIABILITY CHECK")
print("=" * 80)

# 1. v2_marker coverage
print("\n1. v2_marker (control number like C3, C14) coverage:")
cur.execute('''
    SELECT
        COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as has_marker,
        COUNT(*) FILTER (WHERE v2_marker IS NULL OR v2_marker = '') as no_marker,
        COUNT(*) as total
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%' AND v2_is_actionable = true
''')
row = cur.fetchone()
print(f"   Has marker: {row[0]} ({row[0]*100//row[2]}%)")
print(f"   No marker:  {row[1]} ({row[1]*100//row[2]}%)")
print(f"   Total:      {row[2]}")

# 2. v2_topic coverage
print("\n2. v2_topic (LLM-assigned topic) coverage:")
cur.execute('''
    SELECT
        COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as has_topic,
        COUNT(*) FILTER (WHERE v2_topic IS NULL OR v2_topic = '' OR v2_topic = 'None') as no_topic,
        COUNT(*) as total
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%' AND v2_is_actionable = true
''')
row = cur.fetchone()
print(f"   Has topic: {row[0]} ({row[0]*100//row[2]}%)")
print(f"   No topic:  {row[1]} ({row[1]*100//row[2]}%)")

# 3. v2_applicable_dev_types coverage
print("\n3. v2_applicable_dev_types coverage:")
cur.execute('''
    SELECT
        COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NOT NULL AND array_length(v2_applicable_dev_types, 1) > 0) as has_devtype,
        COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NULL OR array_length(v2_applicable_dev_types, 1) IS NULL) as no_devtype,
        COUNT(*) as total
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%' AND v2_is_actionable = true
''')
row = cur.fetchone()
print(f"   Has dev types: {row[0]} ({row[0]*100//row[2]}%)")
print(f"   No dev types:  {row[1]} ({row[1]*100//row[2]}%)")

# 4. Show actual dual_occupancy provisions
print("\n" + "=" * 80)
print("4. SAMPLE: Provisions tagged for 'dual_occupancy' + topic 'Setbacks'")
print("=" * 80)
cur.execute('''
    SELECT v2_marker, v2_dcp_part, v2_provision_type, LEFT(provision_text, 250)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND 'dual_occupancy' = ANY(v2_applicable_dev_types)
    AND v2_topic = 'Setbacks'
    LIMIT 8
''')
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n--- Provision {i} ---")
    print(f"Marker: {row[0] or 'NONE'}")
    print(f"Part: {row[1]}")
    print(f"Type: {row[2]}")
    print(f"Text: {row[3]}...")

# 5. Show parking provisions
print("\n" + "=" * 80)
print("5. SAMPLE: Provisions tagged for 'dual_occupancy' + topic 'Parking'")
print("=" * 80)
cur.execute('''
    SELECT v2_marker, v2_dcp_part, v2_provision_type, LEFT(provision_text, 250)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND 'dual_occupancy' = ANY(v2_applicable_dev_types)
    AND v2_topic = 'Parking'
    LIMIT 8
''')
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n--- Provision {i} ---")
    print(f"Marker: {row[0] or 'NONE'}")
    print(f"Part: {row[1]}")
    print(f"Type: {row[2]}")
    print(f"Text: {row[3]}...")

# 6. Count by topic for dual_occupancy
print("\n" + "=" * 80)
print("6. Provision counts by topic for 'dual_occupancy'")
print("=" * 80)
cur.execute('''
    SELECT v2_topic, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND 'dual_occupancy' = ANY(v2_applicable_dev_types)
    GROUP BY v2_topic
    ORDER BY COUNT(*) DESC
    LIMIT 15
''')
for row in cur.fetchall():
    print(f"   {row[0] or 'NULL'}: {row[1]}")

conn.close()
