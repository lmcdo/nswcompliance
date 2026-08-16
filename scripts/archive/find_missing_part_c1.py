#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find where the 1,285 missing Part C Section 1 provisions are.

Database has 1,554 Part C Section 1 generic provisions
API returns 269 Part C Section 1 provisions
Missing: 1,285
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
print("FINDING 1,285 MISSING PART C SECTION 1 PROVISIONS")
print("=" * 80)

# 1. Verify count
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
""")
total_c1_generic = cur.fetchone()[0]
print(f"\n1. Total Part C Section 1 in generic layer: {total_c1_generic:,}")

# 2. Check if some are in other layers
cur.execute("""
    SELECT
        v2_dcp_layer,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_part LIKE 'Part C Section 1%'
    GROUP BY v2_dcp_layer
    ORDER BY count DESC
""")
print(f"\n2. Part C Section 1 by layer:")
for row in cur.fetchall():
    print(f"   {(row[0] or 'NULL'):15s} {row[1]:5d}")

# 3. Check topic distribution (maybe heritage filtering?)
cur.execute("""
    SELECT
        v2_topic,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
    GROUP BY v2_topic
    ORDER BY count DESC
""")
print(f"\n3. Part C Section 1 generic layer by topic:")
topics = cur.fetchall()
for row in topics[:15]:
    print(f"   {(row[0] or 'NULL'):30s} {row[1]:5d}")

# 4. Check if heritage filtering is the issue
heritage_count = sum(row[1] for row in topics if row[0] and 'heritage' in row[0].lower())
print(f"\n4. Heritage provisions in Part C Section 1: {heritage_count}")

# 5. Check text duplication (maybe many have identical text?)
cur.execute("""
    SELECT COUNT(DISTINCT (LEFT(provision_text, 100), pdf_page))
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
""")
unique_text = cur.fetchone()[0]
print(f"\n5. Unique text+page combinations: {unique_text:,}")
print(f"   Total provisions: {total_c1_generic:,}")
print(f"   Duplicates: {total_c1_generic - unique_text:,} ({(total_c1_generic - unique_text)/total_c1_generic*100:.1f}%)")

if unique_text < 300:
    print(f"\n   🎯 FOUND IT! Massive text duplication")
    print(f"      API deduplication reduces {total_c1_generic:,} provisions to ~{unique_text:,}")
    print(f"      This accounts for the missing 1,285 provisions")

# 6. Check page distribution (maybe many on same page?)
cur.execute("""
    SELECT
        pdf_page,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
    GROUP BY pdf_page
    ORDER BY count DESC
    LIMIT 10
""")
print(f"\n6. Top pages by provision count:")
for row in cur.fetchall():
    page = row[0] if row[0] is not None else 'NULL'
    print(f"   Page {str(page):6s} {row[1]:5d} provisions")

# 7. Sample duplicate provisions
cur.execute("""
    SELECT
        LEFT(provision_text, 100) as text,
        pdf_page,
        COUNT(*) as count,
        STRING_AGG(id::text, ', ') as ids
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_is_actionable = true
      AND is_current = TRUE
      AND v2_dcp_layer = 'generic'
      AND v2_dcp_part LIKE 'Part C Section 1%'
    GROUP BY LEFT(provision_text, 100), pdf_page
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
    LIMIT 5
""")
print(f"\n7. Most duplicated provisions (text+page):")
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\n   {i}. {row[2]} duplicates on page {row[1]}")
    print(f"      IDs: {row[3][:50]}...")
    print(f"      Text: {row[0]}...")

print(f"\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if unique_text < 300:
    print(f"\n✅ TEXT DUPLICATION is the root cause")
    print(f"   - Database: {total_c1_generic:,} Part C Section 1 provisions")
    print(f"   - Unique text+page: {unique_text:,}")
    print(f"   - API dedup removes: {total_c1_generic - unique_text:,} duplicates")
    print(f"   - API returns: ~{unique_text:,} provisions")
    print(f"\n   This explains the 2,309 generic → 342 returned drop")
    print(f"   The database has massive duplication after the rebuild")
else:
    print(f"\n❓ Need to investigate other factors")

print(f"\n" + "=" * 80)

conn.close()
