#!/usr/bin/env python3
"""Analyze provision creation dates and distribution"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 60)
print("PROVISION ANALYSIS")
print("=" * 60)

# Total count
cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
total = cur.fetchone()[0]
print(f"\nTotal provisions: {total}")

# Check provision distribution by v2_dcp_layer
cur.execute("""
    SELECT v2_dcp_layer, COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY v2_dcp_layer
    ORDER BY count DESC
""")
print(f"\nProvisions by DCP layer:")
for row in cur.fetchall():
    layer = row[0] or 'NULL'
    print(f"  {layer}: {row[1]} provisions")

# Check provision distribution by document type
cur.execute("""
    SELECT
        CASE
            WHEN document_id LIKE '%DCP%' THEN 'DCP'
            WHEN document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental%' THEN 'SEPP'
            WHEN document_id LIKE '%LEP%' THEN 'LEP'
            ELSE 'Other'
        END as doc_type,
        COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY doc_type
    ORDER BY count DESC
""")
print(f"\nProvisions by document type:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} provisions")

# Check top documents
cur.execute("""
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 10
""")
print(f"\nTop 10 documents by provision count:")
for row in cur.fetchall():
    doc = row[0][:60] + '...' if len(row[0]) > 60 else row[0]
    print(f"  {doc}: {row[1]}")

# Check v2 columns population
cur.execute("""
    SELECT
        COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as has_topic,
        COUNT(*) FILTER (WHERE v2_applicable_zones IS NOT NULL) as has_zones,
        COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NOT NULL) as has_dev_types,
        COUNT(*) FILTER (WHERE v2_is_actionable IS NOT NULL) as has_actionable
    FROM regulatory_provisions
""")
result = cur.fetchone()
print(f"\nv2 column population:")
print(f"  v2_topic: {result[0]} / {total} ({100*result[0]/total:.1f}%)")
print(f"  v2_applicable_zones: {result[1]} / {total} ({100*result[1]/total:.1f}%)")
print(f"  v2_applicable_dev_types: {result[2]} / {total} ({100*result[2]/total:.1f}%)")
print(f"  v2_is_actionable: {result[3]} / {total} ({100*result[3]/total:.1f}%)")

conn.close()
print("\n" + "=" * 60)
