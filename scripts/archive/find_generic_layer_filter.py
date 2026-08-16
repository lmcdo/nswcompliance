#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find what's filtering out 85% of Leichhardt generic provisions.

Database has: 2,309 generic provisions
API returns: 342 generic provisions
Missing: 1,967 provisions (85%)

Check all possible filters that could cause this.
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
print("FIND GENERIC LAYER FILTER")
print("=" * 80)

# 1. Base count (what database has)
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
""")
base_count = cur.fetchone()[0]
print(f"\n1. BASE COUNT (database): {base_count:,}")

# 2. Check topic filter
cur.execute("""
    SELECT
        v2_topic,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
    GROUP BY v2_topic
    ORDER BY count DESC
""")
print("\n2. BY TOPIC:")
topics = cur.fetchall()
for row in topics[:15]:
    print(f"   {(row[0] or 'NULL'):30s} {row[1]:5d}")

# 3. Check if heritage filter is excluding provisions
# API line 764-766: exclude heritage if not heritage property
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))
""")
without_heritage = cur.fetchone()[0]
heritage_removed = base_count - without_heritage
print(f"\n3. HERITAGE FILTER:")
print(f"   Without heritage filter: {base_count:,}")
print(f"   With heritage filter: {without_heritage:,}")
print(f"   Removed by heritage filter: {heritage_removed:,}")

# 4. Check display_behavior filter
cur.execute("""
    SELECT
        v2_display_behavior,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
    GROUP BY v2_display_behavior
    ORDER BY count DESC
""")
print(f"\n4. BY v2_display_behavior:")
for row in cur.fetchall():
    behavior = row[0] or 'NULL'
    print(f"   {behavior:30s} {row[1]:5d}")

# 5. Check provision_type filter
cur.execute("""
    SELECT
        v2_provision_type,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
    GROUP BY v2_provision_type
    ORDER BY count DESC
""")
print(f"\n5. BY v2_provision_type:")
for row in cur.fetchall():
    prov_type = row[0] or 'NULL'
    print(f"   {prov_type:30s} {row[1]:5d}")

# 6. Check DCP part distribution
cur.execute("""
    SELECT
        v2_dcp_part,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
    GROUP BY v2_dcp_part
    ORDER BY count DESC
""")
print(f"\n6. BY v2_dcp_part:")
parts = cur.fetchall()
for row in parts[:15]:
    print(f"   {(row[0] or 'NULL'):40s} {row[1]:5d}")

# 7. Critical: Check if Part C Section 1 is being filtered
part_c_section_1 = [p for p in parts if p[0] and 'Part C' in p[0] and 'Section 1' in p[0]]
if part_c_section_1:
    part_c_count = sum(p[1] for p in part_c_section_1)
    print(f"\n   [!] Part C Section 1: {part_c_count:,} provisions")
    if part_c_count > 1000:
        print(f"       This is a MAJOR part of the DCP")

# 8. Sample provisions that should be included but might be filtered
print(f"\n7. SAMPLE PROVISIONS (first 10 from most common part):")
if parts:
    most_common_part = parts[0][0]
    cur.execute("""
        SELECT
            id,
            v2_dcp_part,
            v2_topic,
            v2_display_behavior,
            LEFT(provision_text, 80)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_is_actionable = true
          AND is_current = TRUE
          AND v2_dcp_layer = 'generic'
          AND v2_dcp_part = %s
        LIMIT 10
    """, (most_common_part,))

    for i, row in enumerate(cur.fetchall(), 1):
        print(f"\n   {i}. ID {row[0]}")
        print(f"      Part: {row[1]}, Topic: {row[2]}, Behavior: {row[3]}")
        print(f"      Text: {row[4]}...")

# 9. Hypothesis: Check if API is filtering by display_behavior
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND (v2_display_behavior IS NULL OR v2_display_behavior != 'hidden')
""")
visible_count = cur.fetchone()[0]

print(f"\n" + "=" * 80)
print("HYPOTHESIS TESTING")
print("=" * 80)

print(f"\n1. IF filtering by v2_display_behavior != 'hidden':")
print(f"   Base: {base_count:,}")
print(f"   Visible: {visible_count:,}")
print(f"   Hidden: {base_count - visible_count:,}")

# Check what combination of filters gives us 342
print(f"\n2. FINDING FILTER COMBINATION THAT GIVES 342:")

# Try: no heritage + specific topics only
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))
      AND v2_topic IS NOT NULL
""")
count_a = cur.fetchone()[0]
print(f"   No heritage + topic NOT NULL: {count_a:,}")

# Try: specific v2_dcp_part pattern
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
""")
count_b = cur.fetchone()[0]
print(f"   Part C Section 1 only: {count_b:,}")

# Try: Part C Section 2 only
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 2%'
""")
count_c = cur.fetchone()[0]
print(f"   Part C Section 2 only: {count_c:,}")

# Try: exclude Part C Section 1
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND (v2_dcp_part NOT LIKE 'Part C Section 1%' OR v2_dcp_part IS NULL)
""")
count_d = cur.fetchone()[0]
print(f"   EXCLUDE Part C Section 1: {count_d:,}")

if count_d == 342:
    print(f"\n   🎯 FOUND IT! API is EXCLUDING Part C Section 1")
    print(f"      This removes {base_count - count_d:,} provisions")
    print(f"      Part C Section 1 is {(base_count - count_d) / base_count * 100:.1f}% of generic layer")

print(f"\n" + "=" * 80)

conn.close()
