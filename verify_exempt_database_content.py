#!/usr/bin/env python3
"""
Step 1: Verify Database Content for Exempt & Complying Development Codes

Analyzes existing database provisions to understand:
- How many provisions exist
- What document_id formats are used
- What zones are covered
- What development types are mentioned
- Text quality and length
"""
from db_config import get_connection
import re
from collections import Counter

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("EXEMPT & COMPLYING DEVELOPMENT CODES - DATABASE VERIFICATION")
print("=" * 80)

# 1. Count provisions by document_id
print("\n1. PROVISIONS BY DOCUMENT_ID")
print("-" * 80)
cur.execute("""
    SELECT
        document_id,
        COUNT(*) as provision_count,
        extraction_method,
        AVG(LENGTH(provision_text))::int as avg_text_length,
        MIN(LENGTH(provision_text)) as min_length,
        MAX(LENGTH(provision_text)) as max_length
    FROM regulatory_provisions
    WHERE document_id ILIKE '%exempt%'
       OR document_id ILIKE '%complying%'
    GROUP BY document_id, extraction_method
    ORDER BY provision_count DESC
    LIMIT 20
""")

total_provisions = 0
document_groups = {}

for row in cur.fetchall():
    doc_id, count, method, avg_len, min_len, max_len = row
    total_provisions += count

    # Group by base document name
    base_name = doc_id.split('_section_')[0] if '_section_' in doc_id else doc_id
    if base_name not in document_groups:
        document_groups[base_name] = {'count': 0, 'sections': []}
    document_groups[base_name]['count'] += count
    document_groups[base_name]['sections'].append(doc_id)

    print(f"\n{doc_id[:70]}...")
    print(f"  Provisions: {count}")
    print(f"  Method: {method}")
    print(f"  Text length: {avg_len} avg (range: {min_len}-{max_len})")

print(f"\n{'='*80}")
print(f"TOTAL PROVISIONS: {total_provisions:,}")
print(f"DOCUMENT GROUPS: {len(document_groups)}")

# 2. Analyze document grouping
print(f"\n2. DOCUMENT GROUPING ANALYSIS")
print("-" * 80)
for base_name, info in document_groups.items():
    sections = len(info['sections'])
    print(f"\n{base_name[:70]}...")
    print(f"  Total provisions: {info['count']:,}")
    print(f"  Split into: {sections} sections")
    if sections > 1:
        print(f"  Section format: {info['sections'][0]}")
        print(f"                  {info['sections'][1]}")
        print(f"                  ...")

# 3. Sample provisions to understand structure
print(f"\n3. SAMPLE PROVISIONS (Understanding Structure)")
print("-" * 80)
cur.execute("""
    SELECT
        id,
        document_id,
        ref_number,
        section_header,
        provision_text,
        zone,
        development_type,
        LENGTH(provision_text) as text_len
    FROM regulatory_provisions
    WHERE document_id ILIKE '%exempt%'
       OR document_id ILIKE '%complying%'
    ORDER BY RANDOM()
    LIMIT 10
""")

samples = cur.fetchall()
for i, row in enumerate(samples, 1):
    prov_id, doc_id, ref_num, header, text, zone, dev_type, text_len = row

    print(f"\n--- Sample {i} ---")
    print(f"ID: {prov_id}")
    print(f"Ref: {ref_num}")
    print(f"Header: {header}")
    print(f"Zone: {zone or 'NULL'}")
    print(f"Dev Type: {dev_type or 'NULL'}")
    print(f"Text Length: {text_len} chars")
    print(f"Text Preview: {text[:150]}...")

# 4. Analyze zone coverage
print(f"\n4. ZONE COVERAGE")
print("-" * 80)
cur.execute("""
    SELECT
        zone,
        COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
      AND zone IS NOT NULL
      AND zone != ''
    GROUP BY zone
    ORDER BY provision_count DESC
    LIMIT 20
""")

zone_rows = cur.fetchall()
if zone_rows:
    print("Zones with provisions:")
    for zone, count in zone_rows:
        print(f"  {zone:10} {count:,} provisions")
else:
    print("⚠️  NO ZONES TAGGED (zone field is NULL or empty)")

# 5. Analyze development_type coverage
print(f"\n5. DEVELOPMENT TYPE COVERAGE")
print("-" * 80)
cur.execute("""
    SELECT
        development_type,
        COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
      AND development_type IS NOT NULL
      AND development_type != ''
    GROUP BY development_type
    ORDER BY provision_count DESC
    LIMIT 20
""")

dev_type_rows = cur.fetchall()
if dev_type_rows:
    print("Development types with provisions:")
    for dev_type, count in dev_type_rows:
        print(f"  {dev_type:30} {count:,} provisions")
else:
    print("⚠️  NO DEVELOPMENT TYPES TAGGED (development_type field is NULL or empty)")

# 6. Check for structured data in provision_text
print(f"\n6. TEXT CONTENT ANALYSIS (Parsing Opportunities)")
print("-" * 80)

cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
      AND LENGTH(provision_text) > 100
    LIMIT 500
""")

texts = [row[0] for row in cur.fetchall()]

# Analyze text patterns
patterns = {
    'mentions_zone': sum(1 for t in texts if re.search(r'\bzone\b|\bR[0-9]\b|\bB[0-9]\b|\bIN[0-9]\b', t, re.I)),
    'mentions_height': sum(1 for t in texts if re.search(r'\bheight\b|\bmetres?\b|\bmm\b', t, re.I)),
    'mentions_area': sum(1 for t in texts if re.search(r'\barea\b|\bm2\b|square metres?', t, re.I)),
    'mentions_setback': sum(1 for t in texts if re.search(r'\bsetback\b|\bboundary\b', t, re.I)),
    'has_numeric_values': sum(1 for t in texts if re.search(r'\b\d+\.?\d*\s*(m|metres?|mm|millimetres?|sqm|m2)\b', t, re.I)),
    'mentions_exempt': sum(1 for t in texts if re.search(r'\bexempt\b', t, re.I)),
    'mentions_complying': sum(1 for t in texts if re.search(r'\bcomplying\b', t, re.I)),
    'mentions_development': sum(1 for t in texts if re.search(r'\bdevelopment for\b', t, re.I)),
}

print(f"Analyzed {len(texts)} provisions:")
for pattern, count in patterns.items():
    percentage = (count / len(texts)) * 100 if texts else 0
    print(f"  {pattern:25} {count:4} provisions ({percentage:.1f}%)")

# 7. Check if development_controls table has any exempt data
print(f"\n7. DEVELOPMENT_CONTROLS INTEGRATION")
print("-" * 80)
cur.execute("""
    SELECT
        dc.control_type,
        COUNT(*) as count
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE (rp.document_id ILIKE '%exempt%' OR rp.document_id ILIKE '%complying%')
    GROUP BY dc.control_type
    ORDER BY count DESC
""")

control_rows = cur.fetchall()
if control_rows:
    print("[OK] Extracted controls exist:")
    for control_type, count in control_rows:
        print(f"  {control_type:20} {count:,} controls")
else:
    print("[NONE] NO CONTROLS EXTRACTED (development_controls table is empty for exempt codes)")

# 8. Check if development_permissions table has any exempt data
print(f"\n8. DEVELOPMENT_PERMISSIONS INTEGRATION")
print("-" * 80)
cur.execute("""
    SELECT
        permission_status,
        COUNT(*) as count
    FROM development_permissions dp
    WHERE source_type ILIKE '%exempt%'
       OR source_type ILIKE '%complying%'
    GROUP BY permission_status
    ORDER BY count DESC
""")

perm_rows = cur.fetchall()
if perm_rows:
    print("[OK] Permission records exist:")
    for status, count in perm_rows:
        print(f"  {status:20} {count:,} permissions")
else:
    print("[NONE] NO PERMISSIONS RECORDED (development_permissions table is empty for exempt codes)")

# 9. Example provision with rich content
print(f"\n9. EXAMPLE HIGH-VALUE PROVISION")
print("-" * 80)
cur.execute("""
    SELECT
        id,
        ref_number,
        section_header,
        provision_text,
        LENGTH(provision_text) as text_len
    FROM regulatory_provisions
    WHERE (document_id ILIKE '%exempt%' OR document_id ILIKE '%complying%')
      AND LENGTH(provision_text) > 200
      AND (provision_text ILIKE '%development for%'
           OR provision_text ILIKE '%standards%')
    ORDER BY LENGTH(provision_text) DESC
    LIMIT 1
""")

example = cur.fetchone()
if example:
    ex_id, ex_ref, ex_header, ex_text, ex_len = example
    print(f"Provision ID: {ex_id}")
    print(f"Reference: {ex_ref}")
    print(f"Header: {ex_header}")
    print(f"Text Length: {ex_len} chars")
    print(f"\nFull Text:\n{ex_text[:800]}...")
    print(f"\n[...{ex_len - 800} more characters...]")

# 10. Summary and recommendations
print(f"\n{'='*80}")
print("SUMMARY & RECOMMENDATIONS")
print("=" * 80)

print(f"\n[OK] Database contains {total_provisions:,} Exempt/Complying provisions")
print(f"[OK] Extracted using: autoschema method (140 chars avg)")

if not zone_rows:
    print(f"\n[WARN] CRITICAL: No zone tagging")
    print(f"   -> Provisions cannot be filtered by zone (R1, R2, etc.)")
    print(f"   -> Need to extract zone info from provision_text")

if not dev_type_rows:
    print(f"\n[WARN] CRITICAL: No development_type tagging")
    print(f"   -> Provisions cannot be filtered by development (deck, shed, etc.)")
    print(f"   -> Need to extract dev type from provision_text")

if not control_rows:
    print(f"\n[WARN] CRITICAL: No structured controls")
    print(f"   -> No height/area/setback rules in development_controls table")
    print(f"   -> Need to extract numeric standards from provision_text")

if not perm_rows:
    print(f"\n[WARN] CRITICAL: No permission status")
    print(f"   -> No exempt/complying status in development_permissions table")
    print(f"   -> Need to determine which provisions are exempt vs complying")

print(f"\nNEXT STEPS:")
print(f"  1. Extract zone + development_type from provision_text")
print(f"  2. Parse numeric standards -> development_controls table")
print(f"  3. Determine exempt/complying status -> development_permissions table")
print(f"  4. Update API to query structured data")
print(f"  5. Update UI to display exempt development options")

conn.close()

print(f"\n{'='*80}")
print("VERIFICATION COMPLETE")
print("=" * 80)
