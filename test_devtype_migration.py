#!/usr/bin/env python3
"""Test how many DCP provisions we can tag with dev types."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('TESTING DEVELOPMENT TYPE TAGGING MIGRATION')
print('='*80)

# Current state
print('\n1. CURRENT STATE (Before Migration)')
print('-' * 80)
cursor.execute("""
    SELECT
        CASE
            WHEN development_type IS NOT NULL THEN 'Tagged'
            ELSE 'Untagged'
        END as status,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
    GROUP BY status
""")
rows = cursor.fetchall()
for r in rows:
    pct = r['count'] / 15136 * 100 if 15136 > 0 else 0
    print(f"  {r['status']:<20} {r['count']:>6} provisions ({pct:>5.1f}%)")

# Test how many WOULD be tagged by section header patterns
print('\n2. SIMULATION: How many can we tag by section headers?')
print('-' * 80)

patterns = {
    'dwelling_house': ['%dwelling house%', '%single dwelling%', '%F.1%', '%3.1 %'],
    'secondary_dwelling': ['%secondary dwelling%', '%F.2%', '%3.2 %'],
    'shop_top_housing': ['%shop top%', '%F.3%', '%3.3 %'],
    'multi_dwelling': ['%multi dwelling%', '%multi-dwelling%', '%F.4%', '%3.4 %'],
    'residential_flat_building': ['%residential flat%', '%rfb%', '%F.5%', '%3.5 %'],
    'boarding_house': ['%boarding house%', '%F.6%', '%3.6 %'],
    'residential_care': ['%residential care%', '%aged care%', '%F.7%', '%3.7 %'],
    'child_care': ['%child care%', '%childcare%', '%F.8%', '%3.8 %'],
    'commercial': ['%commercial%', '%F.9%', '%3.9 %'],
    'dual_occupancy': ['%dual occupancy%'],
    'townhouse': ['%townhouse%'],
}

total_would_tag = 0
for dev_type, patterns_list in patterns.items():
    like_conditions = ' OR '.join(['LOWER(section_header) LIKE %s' for _ in patterns_list])
    query = f"""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id LIKE '%DCP%'
          AND development_type IS NULL
          AND ({like_conditions})
    """
    cursor.execute(query, patterns_list)
    result = cursor.fetchone()
    count = result['count']
    total_would_tag += count
    if count > 0:
        print(f"  {dev_type:<30} {count:>6} provisions")

print('-' * 80)
print(f"  {'TOTAL NEW TAGS':<30} {total_would_tag:>6} provisions")

# Calculate new totals
cursor.execute("SELECT COUNT(*) as count FROM regulatory_provisions WHERE document_id LIKE '%DCP%' AND development_type IS NOT NULL")
current_tagged = cursor.fetchone()['count']
new_total = current_tagged + total_would_tag
new_pct = new_total / 15136 * 100

print(f"\n  After migration:")
print(f"    Tagged:   {new_total:>6} / 15,136 ({new_pct:>5.1f}%)")
print(f"    Untagged: {15136 - new_total:>6} / 15,136 ({100-new_pct:>5.1f}%)")

# Sample what we'd tag
print('\n3. SAMPLE: Provisions that WOULD be tagged')
print('-' * 80)
cursor.execute("""
    SELECT section_header, ref_number
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
      AND development_type IS NULL
      AND (LOWER(section_header) LIKE '%dwelling house%'
           OR LOWER(section_header) LIKE '%multi dwelling%')
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    section = r['section_header'][:70] if r['section_header'] else 'N/A'
    print(f"  [{r['ref_number']:<15}] {section}")

# Check what's left untagged
print('\n4. SAMPLE: What remains UNTAGGED after migration?')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT section_header
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
      AND development_type IS NULL
      AND section_header IS NOT NULL
      AND NOT (
        LOWER(section_header) LIKE '%dwelling%'
        OR LOWER(section_header) LIKE '%boarding%'
        OR LOWER(section_header) LIKE '%care%'
        OR LOWER(section_header) LIKE '%commercial%'
        OR LOWER(section_header) LIKE '%shop%'
        OR LOWER(section_header) LIKE '%townhouse%'
      )
    LIMIT 20
""")
rows = cursor.fetchall()
print("  General provisions (apply to ALL dev types):")
for r in rows:
    print(f"    {r['section_header'][:70]}")

cursor.close()
conn.close()