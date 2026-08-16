#!/usr/bin/env python3
"""
Provision quality analysis for ALL councils.
Outputs data for the context doc.
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

for council in ['leichhardt', 'ashfield', 'marrickville']:
    print("\n" + "="*70)
    print(f"{council.upper()} DATA PROFILE")
    print("="*70)

    # Overall stats
    cur.execute(f"""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
            COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as has_marker,
            COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as has_page
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
    """)
    total, actionable, has_marker, has_page = cur.fetchone()
    print(f"\nTotal provisions: {total}")
    print(f"Actionable: {actionable} ({100*actionable//total if total else 0}%)")
    print(f"Has v2_marker: {has_marker} ({100*has_marker//total if total else 0}%)")
    print(f"Has pdf_page: {has_page} ({100*has_page//total if total else 0}%)")

    # By DCP part
    print(f"\nBy DCP Part:")
    cur.execute(f"""
        SELECT v2_dcp_part, COUNT(*),
               COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as with_marker
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        GROUP BY v2_dcp_part
        ORDER BY COUNT(*) DESC
    """)
    print(f"{'Part':<30} {'Count':>8} {'Markers':>10} {'%':>6}")
    print("-"*56)
    for part, count, with_marker in cur.fetchall():
        pct = 100*with_marker//count if count else 0
        print(f"{(part or 'NULL'):<30} {count:>8} {with_marker:>10} {pct:>5}%")

    # Sample markers
    print(f"\nSample markers:")
    cur.execute(f"""
        SELECT DISTINCT v2_marker
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        AND v2_marker IS NOT NULL AND v2_marker != ''
        LIMIT 15
    """)
    markers = [r[0] for r in cur.fetchall()]
    print(f"  {', '.join(markers[:15])}")

conn.close()
