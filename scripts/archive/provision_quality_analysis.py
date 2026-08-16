#!/usr/bin/env python3
"""
Comprehensive analysis of provision quality and data issues.
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("PROVISION QUALITY ANALYSIS - LEICHHARDT")
print("="*70)

# 1. Overall stats
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
        COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as has_marker,
        COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as has_page
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
""")
total, actionable, has_marker, has_page = cur.fetchone()
print(f"\n1. OVERALL STATS:")
print(f"   Total provisions: {total}")
print(f"   Marked actionable: {actionable} ({100*actionable//total}%)")
print(f"   Has v2_marker: {has_marker} ({100*has_marker//total}%)")
print(f"   Has pdf_page: {has_page} ({100*has_page//total}%)")

# 2. Actionable provisions by part
print(f"\n2. ACTIONABLE PROVISIONS BY DCP PART:")
cur.execute("""
    SELECT v2_dcp_part, COUNT(*),
           COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as with_marker
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    GROUP BY v2_dcp_part
    ORDER BY COUNT(*) DESC
""")
for part, count, with_marker in cur.fetchall():
    pct = 100*with_marker//count if count else 0
    print(f"   {part or 'NULL':25} {count:5} provisions, {with_marker:4} ({pct:2}%) have markers")

# 3. Check for TOC/intro provisions incorrectly marked actionable
print(f"\n3. LIKELY NON-ACTIONABLE (TOC/intro) marked as actionable:")
cur.execute("""
    SELECT COUNT(*), LEFT(provision_text, 100)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (
        provision_text LIKE '%........%'
        OR provision_text LIKE 'A1.%'
        OR provision_text LIKE 'SECTION%'
        OR provision_text LIKE '%TABLE OF CONTENTS%'
        OR provision_text LIKE 'This Development Control Plan%'
    )
    GROUP BY LEFT(provision_text, 100)
    LIMIT 10
""")
toc_count = 0
for count, text in cur.fetchall():
    toc_count += count
    print(f"   ({count}) {text[:70]}...")
print(f"   TOTAL likely non-actionable: {toc_count}")

# 4. Part C Section 1 analysis (the controls with C# markers)
print(f"\n4. PART C SECTION 1 - GENERAL CONTROLS:")
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as with_marker,
        COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as with_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 1'
""")
total, with_marker, with_topic = cur.fetchone()
print(f"   Total: {total}")
print(f"   Has marker: {with_marker} ({100*with_marker//total if total else 0}%)")
print(f"   Has topic: {with_topic} ({100*with_topic//total if total else 0}%)")

# 5. Part C Section 2 analysis (neighbourhood controls)
print(f"\n5. PART C SECTION 2 - NEIGHBOURHOOD CONTROLS:")
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as with_marker,
        COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as with_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 2'
""")
total, with_marker, with_topic = cur.fetchone()
print(f"   Total: {total}")
print(f"   Has marker: {with_marker} ({100*with_marker//total if total else 0}%)")
print(f"   Has topic: {with_topic} ({100*with_topic//total if total else 0}%)")

# Sample Part C Section 2 provisions
print(f"\n   Sample Part C Section 2 provisions:")
cur.execute("""
    SELECT v2_marker, v2_topic, LEFT(provision_text, 120)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 2'
    LIMIT 8
""")
for marker, topic, text in cur.fetchall():
    print(f"   {marker or 'NO MARKER':10} | {topic or 'NO TOPIC':15} | {text[:60]}...")

conn.close()
