#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Provision Count Drop After DB Rebuild

User reports:
- BEFORE rebuild: Leichhardt API returned 2k+ provisions
- AFTER rebuild: Leichhardt API returns 800+ provisions

Need to find:
1. Current actual count for Leichhardt
2. What filters are being applied
3. What changed in the database rebuild
"""

import os
import sys
import io
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

# Fix encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found")
    sys.exit(1)

url = urlparse(DATABASE_URL)

def connect_db():
    return psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        cursor_factory=RealDictCursor
    )

def main():
    conn = connect_db()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("PROVISION COUNT INVESTIGATION - LEICHHARDT")
    print("=" * 80)

    # 1. Total Leichhardt provisions in database
    cur.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
    """)
    total_raw = cur.fetchone()['count']
    print(f"\n1. TOTAL PROVISIONS (raw, all rows):")
    print(f"   {total_raw} total Leichhardt provisions in database")

    # 2. With is_current filter (should be same after rebuild)
    cur.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
    """)
    with_is_current = cur.fetchone()['count']
    print(f"\n2. WITH is_current = TRUE:")
    print(f"   {with_is_current} provisions")

    # 3. With v2_is_actionable filter (API uses this)
    cur.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
          AND v2_is_actionable = true
    """)
    with_actionable = cur.fetchone()['count']
    print(f"\n3. WITH v2_is_actionable = true (API FILTER):")
    print(f"   {with_actionable} provisions")
    print(f"   [!] This is what the API returns")

    # 4. Check v2_is_actionable distribution
    cur.execute("""
        SELECT
            v2_is_actionable,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
        GROUP BY v2_is_actionable
        ORDER BY count DESC
    """)
    print(f"\n4. v2_is_actionable DISTRIBUTION:")
    for row in cur.fetchall():
        actionable = row['v2_is_actionable']
        count = row['count']
        label = 'TRUE' if actionable else ('FALSE' if actionable is False else 'NULL')
        print(f"   {label:10s} {count:5d} provisions ({count/with_is_current*100:.1f}%)")

    # 5. Check what makes provisions non-actionable
    cur.execute("""
        SELECT
            v2_provision_type,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
          AND v2_is_actionable = false
        GROUP BY v2_provision_type
        ORDER BY count DESC
        LIMIT 10
    """)
    print(f"\n5. NON-ACTIONABLE PROVISIONS (v2_is_actionable = false):")
    non_actionable = cur.fetchall()
    if non_actionable:
        for row in non_actionable:
            print(f"   {(row['v2_provision_type'] or 'NULL'):20s} {row['count']:5d}")
    else:
        print("   (None - all provisions are either actionable=true or actionable=NULL)")

    # 6. Check NULL actionable provisions
    cur.execute("""
        SELECT
            v2_provision_type,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
          AND v2_is_actionable IS NULL
        GROUP BY v2_provision_type
        ORDER BY count DESC
        LIMIT 10
    """)
    print(f"\n6. NULL ACTIONABLE PROVISIONS (v2_is_actionable IS NULL):")
    null_actionable = cur.fetchall()
    if null_actionable:
        for row in null_actionable:
            print(f"   {(row['v2_provision_type'] or 'NULL'):20s} {row['count']:5d}")

    # 7. Sample non-actionable provisions
    cur.execute("""
        SELECT
            id,
            provision_text,
            v2_provision_type,
            v2_dcp_part,
            v2_is_actionable
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
          AND (v2_is_actionable = false OR v2_is_actionable IS NULL)
        ORDER BY id
        LIMIT 10
    """)
    print(f"\n7. SAMPLE NON-ACTIONABLE/NULL PROVISIONS:")
    for i, row in enumerate(cur.fetchall(), 1):
        actionable = 'FALSE' if row['v2_is_actionable'] is False else 'NULL'
        print(f"\n   {i}. ID {row['id']} [{actionable}]")
        print(f"      Part: {row['v2_dcp_part']}, Type: {row['v2_provision_type']}")
        print(f"      Text: {(row['provision_text'] or '')[:150]}...")

    # 8. Layer distribution
    cur.execute("""
        SELECT
            v2_dcp_layer,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND is_current = TRUE
          AND v2_is_actionable = true
        GROUP BY v2_dcp_layer
        ORDER BY count DESC
    """)
    print(f"\n8. LAYER DISTRIBUTION (actionable only):")
    for row in cur.fetchall():
        print(f"   {(row['v2_dcp_layer'] or 'NULL'):20s} {row['count']:5d}")

    print(f"\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)

    excluded_count = with_is_current - with_actionable
    print(f"\n Total provisions (is_current=true): {with_is_current}")
    print(f" Actionable provisions: {with_actionable}")
    print(f" Excluded by v2_is_actionable filter: {excluded_count}")
    print(f" Exclusion rate: {excluded_count/with_is_current*100:.1f}%")

    if excluded_count > 1000:
        print(f"\n [!] MAJOR FINDING: {excluded_count} provisions excluded by v2_is_actionable filter")
        print("     This likely explains the 2k+ -> 800+ drop")
        print("\n Possible causes:")
        print("     1. Re-enrichment set v2_is_actionable = false for non-controls")
        print("     2. Backup had different v2_is_actionable tagging")
        print("     3. Enrichment scripts changed v2_is_actionable logic")

    print(f"\n" + "=" * 80)

    conn.close()

if __name__ == '__main__':
    main()
