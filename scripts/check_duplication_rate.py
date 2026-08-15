#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check if there's massive duplication in Leichhardt provisions that would explain
2,872 provisions deduplicating down to 834.

API deduplication logic:
1. Deduplicate by provision ID
2. Deduplicate by text content (first 100 chars) + page number
"""

import os, sys, io, psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    host=url.hostname, port=url.port or 5432,
    database=url.path[1:], user=url.username, password=url.password
)
cur = conn.cursor()

print("\n" + "=" * 80)
print("DUPLICATION ANALYSIS - LEICHHARDT")
print("=" * 80)

# 1. Check ID duplication (should be none - IDs are unique)
print("\n1. ID DUPLICATION CHECK:")
cur.execute("""
    SELECT COUNT(*) as total_rows, COUNT(DISTINCT id) as unique_ids
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
""")
row = cur.fetchone()
print(f"   Total rows: {row[0]:,}")
print(f"   Unique IDs: {row[1]:,}")
print(f"   ID duplicates: {row[0] - row[1]:,}")

# 2. Check text content duplication (first 100 chars + page)
print("\n2. TEXT CONTENT DUPLICATION (first 100 chars + page):")
cur.execute("""
    SELECT
        COUNT(*) as total_rows,
        COUNT(DISTINCT (LEFT(provision_text, 100), pdf_page)) as unique_text_page_combos
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
""")
row = cur.fetchone()
total_rows = row[0]
unique_combos = row[1]
duplicates = total_rows - unique_combos
dup_rate = (duplicates / total_rows * 100) if total_rows > 0 else 0

print(f"   Total rows: {total_rows:,}")
print(f"   Unique text+page combos: {unique_combos:,}")
print(f"   Text duplicates: {duplicates:,} ({dup_rate:.1f}%)")

# 3. Find most duplicated text patterns
print("\n3. MOST DUPLICATED TEXT PATTERNS:")
cur.execute("""
    SELECT
        LEFT(provision_text, 100) as text_prefix,
        pdf_page,
        COUNT(*) as occurrences
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
    GROUP BY LEFT(provision_text, 100), pdf_page
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    LIMIT 10
""")
results = cur.fetchall()
if results:
    for i, row in enumerate(results, 1):
        print(f"\n   {i}. {row[2]} occurrences on page {row[1]}")
        print(f"      Text: {row[0]}...")
else:
    print("   (No text duplicates found)")

# 4. Simulate API deduplication
print("\n4. SIMULATING API DEDUPLICATION:")

# Get provisions for a typical query (generic + use_specific + precinct with NULL id)
cur.execute("""
    SELECT id, provision_text, pdf_page, v2_dcp_layer
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
        AND v2_dcp_layer IN ('generic', 'use_specific')
        OR (v2_dcp_layer = 'precinct' AND v2_precinct_id IS NULL)
""")
provisions = cur.fetchall()

print(f"   Total provisions before dedup: {len(provisions):,}")

# Dedupe by ID (should be no-op)
unique_by_id = {}
for p in provisions:
    if p[0] not in unique_by_id:
        unique_by_id[p[0]] = p

print(f"   After ID dedup: {len(unique_by_id):,}")

# Dedupe by text+page
unique_by_text = {}
for p in unique_by_id.values():
    text_key = f"{(p[1] or '')[:100]}|{p[2] or 0}"
    if text_key not in unique_by_text:
        unique_by_text[text_key] = p

print(f"   After text+page dedup: {len(unique_by_text):,}")

removed = len(provisions) - len(unique_by_text)
print(f"   Removed by deduplication: {removed:,} ({removed/len(provisions)*100:.1f}%)")

# 5. Check if precinct layer has excessive provisions
print("\n5. PRECINCT LAYER ANALYSIS:")
cur.execute("""
    SELECT
        v2_precinct_id,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
        AND v2_dcp_layer = 'precinct'
    GROUP BY v2_precinct_id
    ORDER BY count DESC
""")
print("   v2_precinct_id | Count")
print("   ---------------|-------")
for row in cur.fetchall()[:10]:
    precinct = row[0] or 'NULL'
    print(f"   {precinct:14s} | {row[1]:5d}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if dup_rate > 50:
    print(f"\n [!] HIGH DUPLICATION RATE: {dup_rate:.1f}% of provisions are text duplicates")
    print("   This explains the 2,872 -> 834 drop")
    print("\n Possible causes:")
    print("   1. Database has duplicate rows with same text+page")
    print("   2. Multiple provision IDs pointing to same content")
    print("   3. Data quality issue from backup/restore")
elif removed > 1000:
    print(f"\n [!] Deduplication removed {removed:,} provisions")
    print("   This partially explains the count drop")
else:
    print("\n [OK] Duplication rate is normal")
    print("   Deduplication is NOT the main cause of the 2,872 -> 834 discrepancy")
    print("\n Need to investigate:")
    print("   - Are there additional API filters not captured in simulation?")
    print("   - Is the test using different parameters?")
    print("   - Is there frontend filtering after API response?")

print("\n" + "=" * 80)

conn.close()
