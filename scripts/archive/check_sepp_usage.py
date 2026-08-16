#!/usr/bin/env python3
"""Check which SEPPs are actually used/referenced in the system."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 70)
print("SEPP USAGE ANALYSIS - What's Actually Needed?")
print("=" * 70)

# 1. Check what SEPPs are cited in cross-references
print("\n=== SEPPs CITED IN CROSS-REFERENCES ===")
cur.execute("""
    SELECT reference_text, COUNT(*) as refs
    FROM cross_reference_index
    WHERE reference_text ILIKE '%sepp%'
       OR reference_text ILIKE '%state environmental%'
    GROUP BY reference_text
    ORDER BY refs DESC
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"  {row[1]:3}x: {row[0][:60]}")

# 2. Group SEPPs by type and count provisions
print("\n=== SEPP PROVISION COUNTS BY TYPE ===")
cur.execute("""
    SELECT
        CASE
            WHEN document_id ILIKE '%housing%' THEN 'SEPP Housing 2021'
            WHEN document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%' THEN 'SEPP Exempt & Complying'
            WHEN document_id ILIKE '%transport%' THEN 'SEPP Transport & Infrastructure'
            WHEN document_id ILIKE '%biodiversity%' THEN 'SEPP Biodiversity & Conservation'
            WHEN document_id ILIKE '%industry%' OR document_id ILIKE '%employment%' THEN 'SEPP Industry & Employment'
            WHEN document_id ILIKE '%resilience%' OR document_id ILIKE '%hazard%' THEN 'SEPP Resilience & Hazards'
            WHEN document_id ILIKE '%primary%production%' THEN 'SEPP Primary Production'
            WHEN document_id ILIKE '%sustainable%' OR document_id ILIKE '%building%' THEN 'SEPP Sustainable Buildings'
            WHEN document_id ILIKE '%planning%system%' THEN 'SEPP Planning Systems'
            ELSE 'Other SEPP'
        END as sepp_type,
        COUNT(*) as provisions,
        COUNT(DISTINCT document_id) as doc_versions
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%' OR document_id ILIKE '%state_environmental%'
    GROUP BY 1
    ORDER BY provisions DESC
""")
total = 0
for row in cur.fetchall():
    total += row[1]
    print(f"  {row[0]:<35}: {row[1]:>6} provisions ({row[2]} doc versions)")
print(f"  {'TOTAL':<35}: {total:>6}")

# 3. Check what topics are covered by each SEPP
print("\n=== TOPICS BY SEPP TYPE ===")
cur.execute("""
    SELECT
        CASE
            WHEN document_id ILIKE '%housing%' THEN 'Housing'
            WHEN document_id ILIKE '%exempt%' THEN 'Exempt/Complying'
            WHEN document_id ILIKE '%transport%' THEN 'Transport'
            WHEN document_id ILIKE '%biodiversity%' THEN 'Biodiversity'
            WHEN document_id ILIKE '%industry%' THEN 'Industry'
            WHEN document_id ILIKE '%resilience%' THEN 'Resilience'
            ELSE 'Other'
        END as sepp,
        v2_topic,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%sepp%' OR document_id ILIKE '%state_environmental%')
      AND v2_topic IS NOT NULL
    GROUP BY 1, 2
    ORDER BY 1, count DESC
""")
current_sepp = None
for row in cur.fetchall():
    if row[0] != current_sepp:
        current_sepp = row[0]
        print(f"\n  {current_sepp}:")
    if row[2] > 10:  # Only show topics with >10 provisions
        print(f"    - {row[1]}: {row[2]}")

# 4. Recommendation
print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)
print("""
For CDC-only app:
  KEEP: Housing, Exempt & Complying, Sustainable Buildings
  DELETE: Transport, Biodiversity, Industry, Primary Production, Resilience

For CDC + DA app:
  KEEP ALL - but deduplicate (many doc versions exist)

Key question: Does the Planning Portal return SEPP overlay data that
references provisions in these SEPPs? If so, they're needed for DA.
""")

conn.close()
