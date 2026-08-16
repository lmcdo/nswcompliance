#!/usr/bin/env python3
"""
Extract ACTUAL TOC structure from the database.
What sections exist? What page ranges? What markers?
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

print("="*80)
print("EXTRACTING ACTUAL DCP STRUCTURE FROM DATABASE")
print("="*80)

for council in ['leichhardt', 'ashfield', 'marrickville']:
    print(f"\n\n{'#'*80}")
    print(f"# {council.upper()} DCP STRUCTURE")
    print(f"{'#'*80}")

    # Get all distinct document_ids to understand structure
    cur.execute(f"""
        SELECT DISTINCT document_id, COUNT(*) as provision_count,
               MIN(pdf_page) as min_page, MAX(pdf_page) as max_page
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        GROUP BY document_id
        ORDER BY document_id
    """)

    print(f"\n## Document IDs (source files):\n")
    for doc_id, count, min_p, max_p in cur.fetchall():
        page_range = f"p{min_p}-{max_p}" if min_p and max_p else "no pages"
        print(f"  {doc_id[:70]}")
        print(f"      {count} provisions, {page_range}")

    # Get distinct markers
    cur.execute(f"""
        SELECT DISTINCT v2_marker, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        AND v2_marker IS NOT NULL AND v2_marker != ''
        GROUP BY v2_marker
        ORDER BY v2_marker
    """)

    markers = cur.fetchall()
    print(f"\n## Markers found ({len(markers)} unique):\n")
    for marker, cnt in markers:
        print(f"  {marker:<15} ({cnt} provisions)")

    # Get distinct DCP parts
    cur.execute(f"""
        SELECT v2_dcp_part, COUNT(*) as cnt,
               COUNT(*) FILTER (WHERE v2_marker IS NOT NULL AND v2_marker != '') as with_marker
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        GROUP BY v2_dcp_part
        ORDER BY v2_dcp_part
    """)

    print(f"\n## DCP Parts:\n")
    print(f"  {'Part':<30} {'Total':>8} {'Markers':>10}")
    print(f"  {'-'*50}")
    for part, cnt, with_marker in cur.fetchall():
        print(f"  {(part or 'NULL'):<30} {cnt:>8} {with_marker:>10}")

    # For each part, get page ranges
    cur.execute(f"""
        SELECT v2_dcp_part,
               MIN(pdf_page) as min_page,
               MAX(pdf_page) as max_page,
               COUNT(DISTINCT pdf_page) as unique_pages
        FROM regulatory_provisions
        WHERE document_id ILIKE '%{council}%'
        AND v2_is_actionable = true
        AND pdf_page IS NOT NULL
        GROUP BY v2_dcp_part
        ORDER BY MIN(pdf_page)
    """)

    print(f"\n## Page Ranges by Part:\n")
    print(f"  {'Part':<30} {'Pages':>15} {'Unique':>8}")
    print(f"  {'-'*55}")
    for part, min_p, max_p, unique in cur.fetchall():
        print(f"  {(part or 'NULL'):<30} {min_p:>6} - {max_p:<6} {unique:>8}")

conn.close()
