#!/usr/bin/env python3
"""Debug script to understand the baseline metrics."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=== CROSS-REFERENCE RESOLUTION ===")
cur.execute("""
    SELECT
        resolution_status,
        COUNT(*) as count
    FROM cross_reference_index
    GROUP BY resolution_status
    ORDER BY count DESC
""")
total_refs = 0
for row in cur.fetchall():
    total_refs += row[1]
    print(f"  {row[0]}: {row[1]}")
print(f"  TOTAL: {total_refs}")

print("\n=== CROSS-REFS BY SOURCE PROVISION (join to get doc) ===")
cur.execute("""
    SELECT
        rp.document_id,
        COUNT(*) as count,
        SUM(CASE WHEN cri.resolution_status = 'resolved' THEN 1 ELSE 0 END) as resolved
    FROM cross_reference_index cri
    JOIN regulatory_provisions rp ON cri.source_provision_id = rp.id
    GROUP BY rp.document_id
    ORDER BY count DESC
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  {row[0][:50]}: {row[1]} total, {row[2]} resolved")

print("\n=== TOPIC COVERAGE BY DOCUMENT_ID PATTERN ===")
cur.execute("""
    SELECT
        CASE
            WHEN document_id ILIKE '%leichhardt%' THEN 'leichhardt'
            WHEN document_id ILIKE '%ashfield%' THEN 'ashfield'
            WHEN document_id ILIKE '%marrickville%' THEN 'marrickville'
            WHEN document_id ILIKE '%inner%west%' THEN 'inner_west'
            WHEN document_id ILIKE '%sepp%' THEN 'sepp'
            ELSE document_id
        END as source,
        COUNT(*) as total,
        SUM(CASE WHEN v2_topic IS NOT NULL AND v2_topic != '' THEN 1 ELSE 0 END) as has_topic
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    GROUP BY 1
    ORDER BY total DESC
""")
for row in cur.fetchall():
    pct = round(100 * row[2] / row[1], 1) if row[1] > 0 else 0
    print(f"  {row[0][:40]}: {row[1]} total, {row[2]} with topic ({pct}%)")

print("\n=== DISTINCT DOCUMENT_IDS ===")
cur.execute("""
    SELECT DISTINCT document_id, COUNT(*) as provisions
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    GROUP BY document_id
    ORDER BY provisions DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} provisions")

conn.close()
