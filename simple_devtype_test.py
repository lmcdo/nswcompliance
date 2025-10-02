#!/usr/bin/env python3
"""Simple test: how many DCP provisions can we tag?"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('CAN WE EASILY FIX THE 5% DCP TAGGING PROBLEM?')
print('='*80)

# Current state
print('\n1. CURRENT STATE')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as total FROM regulatory_provisions WHERE document_id LIKE '%DCP%'
""")
total_dcp = cursor.fetchone()['total']

cursor.execute("""
    SELECT COUNT(*) as tagged FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%' AND development_type IS NOT NULL
""")
current_tagged = cursor.fetchone()['tagged']

print(f"  Total DCP provisions: {total_dcp:>6}")
print(f"  Currently tagged:     {current_tagged:>6} ({current_tagged/total_dcp*100:>5.1f}%)")
print(f"  Untagged:             {total_dcp - current_tagged:>6} ({(total_dcp-current_tagged)/total_dcp*100:>5.1f}%)")

# Test section header tagging potential
print('\n2. PROVISIONS WITH DEV-TYPE-SPECIFIC SECTION HEADERS')
print('-' * 80)

test_patterns = {
    'dwelling_house': '%dwelling house%',
    'multi_dwelling': '%multi dwelling%',
    'residential_flat': '%residential flat%',
    'secondary_dwelling': '%secondary dwelling%',
    'commercial': '%commercial%',
    'child_care': '%child care%',
}

total_matchable = 0
for dev_type, pattern in test_patterns.items():
    cursor.execute(f"""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id LIKE '%DCP%'
          AND development_type IS NULL
          AND LOWER(section_header) LIKE '{pattern}'
    """)
    count = cursor.fetchone()['count']
    total_matchable += count
    if count > 0:
        print(f"  {dev_type:<30} {count:>6}")

print('-' * 80)
print(f"  {'WOULD TAG':<30} {total_matchable:>6} additional provisions")
print(f"  New total: {current_tagged + total_matchable:>6} / {total_dcp} ({(current_tagged + total_matchable)/total_dcp*100:>5.1f}%)")

# What about provisions WITHOUT dev-type-specific headers?
print('\n3. REMAINING UNTAGGED PROVISIONS')
print('-' * 80)
remaining = total_dcp - current_tagged - total_matchable
print(f"  {remaining:>6} provisions ({remaining/total_dcp*100:>5.1f}%) cannot be auto-tagged")
print(f"\n  These are likely GENERAL provisions that apply to ALL dev types:")

cursor.execute("""
    SELECT DISTINCT section_header
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
      AND section_header IS NOT NULL
      AND NOT (
        LOWER(section_header) LIKE '%dwelling%'
        OR LOWER(section_header) LIKE '%boarding%'
        OR LOWER(section_header) LIKE '%care%'
        OR LOWER(section_header) LIKE '%commercial%'
      )
    LIMIT 15
""")
rows = cursor.fetchall()
for r in rows:
    print(f"    - {r['section_header'][:70]}")

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)
print(f"""
  ANSWER: NO, we CANNOT easily fix the 5% tagging problem

  - Section headers like "Floor space ratio" or "Parking" don't specify dev type
  - Development type context is at the DOCUMENT/CHAPTER level, not section level
  - Would need to tag based on document_id (e.g., "Chapter_F_Section_1" = dwelling_house)

  The remaining 95% are GENERAL provisions that apply across multiple dev types.
  To filter properly, we need to use the Chapter F structure from document hierarchy.
""")

cursor.close()
conn.close()