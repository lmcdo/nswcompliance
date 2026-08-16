#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnose is_current Filter Issue

The API query includes:
  AND regulatory_provisions.is_current = TRUE

This may be filtering out provisions after the database rebuild.
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
print("is_current FILTER INVESTIGATION")
print("=" * 80)

# 1. Check is_current distribution for Leichhardt
print("\n1. is_current DISTRIBUTION (Leichhardt):")
cur.execute("""
    SELECT
        is_current,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as pct
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
    GROUP BY is_current
    ORDER BY count DESC
""")
for row in cur.fetchall():
    current = 'TRUE' if row[0] else ('FALSE' if row[0] is False else 'NULL')
    print(f"   {current:10s} {row[1]:5d} ({row[2]}%)")

# 2. Check what the API filter gives us
print("\n2. API FILTER RESULT (is_current = TRUE):")
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND is_current = TRUE
""")
with_is_current = cur.fetchone()[0]
print(f"   Provisions with is_current=TRUE: {with_is_current:,}")

# 3. Without is_current filter
print("\n3. WITHOUT is_current FILTER:")
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
""")
without_is_current = cur.fetchone()[0]
print(f"   All actionable provisions: {without_is_current:,}")
print(f"   Filtered out by is_current: {without_is_current - with_is_current:,}")

# 4. Check if is_current was set during restore
print("\n4. CHECKING is_current VALUES:")
cur.execute("""
    SELECT
        is_current,
        v2_dcp_layer,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
    GROUP BY is_current, v2_dcp_layer
    ORDER BY is_current, count DESC
""")
print("\n   is_current | Layer        | Count")
print("   -----------|--------------|-------")
for row in cur.fetchall():
    current = 'TRUE' if row[0] else ('FALSE' if row[0] is False else 'NULL')
    layer = row[1] or 'NULL'
    print(f"   {current:10s} | {layer:12s} | {row[2]:5d}")

# 5. Sample provisions with is_current = FALSE or NULL
print("\n5. SAMPLE PROVISIONS WITH is_current != TRUE:")
cur.execute("""
    SELECT
        id,
        is_current,
        v2_dcp_layer,
        v2_dcp_part,
        provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
        AND v2_is_actionable = true
        AND (is_current IS NULL OR is_current = FALSE)
    LIMIT 10
""")
results = cur.fetchall()
if results:
    for i, row in enumerate(results, 1):
        current = 'FALSE' if row[1] is False else 'NULL'
        print(f"\n   {i}. ID {row[0]} [is_current={current}]")
        print(f"      Layer: {row[2]}, Part: {row[3]}")
        print(f"      Text: {(row[4] or '')[:100]}...")
else:
    print("   (All provisions have is_current=TRUE)")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

if with_is_current < without_is_current:
    filtered = without_is_current - with_is_current
    pct = filtered / without_is_current * 100
    print(f"\n [!] is_current filter is removing {filtered:,} provisions ({pct:.1f}%)")
    print(f"\n Actionable provisions: {without_is_current:,}")
    print(f" With is_current=TRUE: {with_is_current:,}")
    print(f" Filtered out: {filtered:,}")

    if pct > 50:
        print(f"\n [CRITICAL] More than 50% of provisions filtered out!")
        print("   This explains the 2,990 -> 834 drop")
        print("\n Possible causes:")
        print("   1. Database restore did NOT set is_current=TRUE")
        print("   2. Backup had is_current=FALSE/NULL for most provisions")
        print("   3. Need to run: UPDATE regulatory_provisions SET is_current=TRUE")
else:
    print("\n [OK] is_current filter not causing the issue")

print("\n" + "=" * 80)

conn.close()
