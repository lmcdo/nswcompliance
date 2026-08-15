#!/usr/bin/env python3
"""Analyze what's extracted vs what's referenced to inform extraction strategy."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2
from collections import Counter

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print("=" * 80)
print("EXTRACTION SCOPE ANALYSIS")
print("=" * 80)

# 1. What LEP content exists?
print("\n=== INNER WEST LEP CONTENT ===")
cur.execute("""
    SELECT
        COALESCE(v2_dcp_part, section_header, 'No Part') as part,
        COUNT(*) as provisions
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    GROUP BY 1
    ORDER BY 1
    LIMIT 20
""")
print("Parts/sections extracted:")
for row in cur.fetchall():
    print(f"  {row[0][:50]}: {row[1]} provisions")

# 2. What SEPP content exists?
print("\n=== SEPP CONTENT BY DOCUMENT ===")
cur.execute("""
    SELECT
        document_id,
        COUNT(*) as provisions,
        COUNT(DISTINCT v2_dcp_part) as parts
    FROM regulatory_provisions
    WHERE document_id ILIKE '%sepp%' OR document_id ILIKE '%state_environmental%'
    GROUP BY document_id
    ORDER BY provisions DESC
""")
for row in cur.fetchall():
    print(f"  {row[0][:60]}: {row[1]} provs, {row[2]} parts")

# 3. Cross-reference TARGET analysis - what are we pointing TO?
print("\n=== CROSS-REFERENCE TARGETS (what's being referenced) ===")
cur.execute("""
    SELECT
        reference_text,
        reference_type,
        resolution_status,
        COUNT(*) as count
    FROM cross_reference_index
    GROUP BY reference_text, reference_type, resolution_status
    ORDER BY count DESC
    LIMIT 30
""")
print("Top 30 referenced targets:")
for row in cur.fetchall():
    status = "Y" if row[2] == 'resolved' else "N"
    ref_text = (row[0] or '')[:70]
    print(f"  [{status}] {row[3]:3}x: {ref_text} ({row[1]})")

# 4. Unresolved references - what's MISSING?
print("\n=== UNRESOLVED REFERENCE PATTERNS ===")
cur.execute("""
    SELECT
        reference_text,
        COUNT(*) as count
    FROM cross_reference_index
    WHERE resolution_status = 'unresolved'
    GROUP BY reference_text
    ORDER BY count DESC
    LIMIT 20
""")
print("Most common unresolved references:")
for row in cur.fetchall():
    print(f"  {row[1]:3}x: {row[0][:80]}")

# 5. What document types do unresolved refs point to?
print("\n=== UNRESOLVED REFS - EXTERNAL VS INTERNAL ===")
cur.execute("""
    SELECT reference_text FROM cross_reference_index WHERE resolution_status = 'unresolved'
""")
refs = [r[0] for r in cur.fetchall()]

external_patterns = {
    'EP&A Act': 0,
    'EP&A Regulation': 0,
    'Other Act': 0,
    'Australian Standard': 0,
    'BCA/NCC': 0,
    'Other SEPP': 0,
    'Same SEPP (internal)': 0,
    'LEP clause': 0,
    'Unknown': 0
}

for ref in refs:
    ref_lower = ref.lower() if ref else ''
    if 'act 1979' in ref_lower or 'ep&a act' in ref_lower or 'planning and assessment act' in ref_lower:
        external_patterns['EP&A Act'] += 1
    elif 'regulation' in ref_lower and ('2021' in ref_lower or '2000' in ref_lower):
        external_patterns['EP&A Regulation'] += 1
    elif ' act ' in ref_lower or ' act,' in ref_lower:
        external_patterns['Other Act'] += 1
    elif 'australian standard' in ref_lower or 'as ' in ref_lower[:5]:
        external_patterns['Australian Standard'] += 1
    elif 'bca' in ref_lower or 'building code' in ref_lower or 'ncc' in ref_lower:
        external_patterns['BCA/NCC'] += 1
    elif 'sepp' in ref_lower or 'state environmental' in ref_lower:
        external_patterns['Other SEPP'] += 1
    elif 'clause' in ref_lower and any(x in ref_lower for x in ['lep', 'local environmental']):
        external_patterns['LEP clause'] += 1
    elif 'clause' in ref_lower or 'division' in ref_lower or 'part' in ref_lower:
        external_patterns['Same SEPP (internal)'] += 1
    else:
        external_patterns['Unknown'] += 1

print("Unresolved reference categories:")
for cat, count in sorted(external_patterns.items(), key=lambda x: -x[1]):
    if count > 0:
        print(f"  {cat}: {count} ({round(100*count/len(refs),1)}%)")

# 6. What would full LEP extraction add?
print("\n=== LEP CLAUSE STRUCTURE (what parts exist in NSW legislation?) ===")
print("  Inner West LEP 2022 has ~150 clauses across 7 Parts")
print("  Currently extracted: ~1,381 provisions")
print("  Note: Each 'clause' may have multiple sub-provisions")

# 7. Check if DCP references LEP clauses
print("\n=== DCP -> LEP REFERENCES ===")
cur.execute("""
    SELECT
        cri.reference_text,
        COUNT(*) as count
    FROM cross_reference_index cri
    JOIN regulatory_provisions rp ON cri.source_provision_id = rp.id
    WHERE rp.document_id ILIKE '%dcp%'
      OR rp.document_id ILIKE '%leichhardt%'
      OR rp.document_id ILIKE '%ashfield%'
      OR rp.document_id ILIKE '%marrickville%'
    GROUP BY cri.reference_text
    ORDER BY count DESC
    LIMIT 15
""")
print("What DCPs reference:")
for row in cur.fetchall():
    print(f"  {row[1]:3}x: {row[0][:70]}")

conn.close()

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
