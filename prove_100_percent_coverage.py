#!/usr/bin/env python3
"""
PROOF: Verify 100% regulatory provision zone coverage claim
"""

import sqlite3

# Define ALL regulatory provision types
REGULATORY_PROVISION_TYPES = [
    'height_limit', 'setback', 'fsr', 'parking', 'landscaping',
    'subdivision', 'provision_height', 'provision_setback',
    'provision_design', 'formal_Planning Controls',
    'building_separation', 'site_coverage', 'minimum_lot_size'
]

conn = sqlite3.connect("nsw_planning.db")
cursor = conn.cursor()

print("=" * 70)
print("PROOF OF 100% REGULATORY PROVISION ZONE COVERAGE")
print("=" * 70)

# 1. Count total regulatory provisions
placeholders = ','.join(['?' for _ in REGULATORY_PROVISION_TYPES])
cursor.execute(f"""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
""", REGULATORY_PROVISION_TYPES)
total_regulatory = cursor.fetchone()[0]

print(f"\n1. TOTAL REGULATORY PROVISIONS: {total_regulatory:,}")
print(f"   Types included: {', '.join(REGULATORY_PROVISION_TYPES[:5])}...")

# 2. Count regulatory provisions WITH zones
cursor.execute(f"""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
    AND zone IS NOT NULL AND zone != ''
""", REGULATORY_PROVISION_TYPES)
regulatory_with_zones = cursor.fetchone()[0]

print(f"\n2. REGULATORY PROVISIONS WITH ZONES: {regulatory_with_zones:,}")

# 3. Count regulatory provisions WITHOUT zones
cursor.execute(f"""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
    AND (zone IS NULL OR zone = '')
""", REGULATORY_PROVISION_TYPES)
regulatory_without_zones = cursor.fetchone()[0]

print(f"\n3. REGULATORY PROVISIONS WITHOUT ZONES: {regulatory_without_zones}")

# 4. Calculate coverage percentage
coverage = (regulatory_with_zones / total_regulatory * 100) if total_regulatory > 0 else 0
print(f"\n4. REGULATORY PROVISION ZONE COVERAGE: {coverage:.1f}%")

# 5. Show specific examples of regulatory provisions WITH zones
print("\n5. SAMPLE REGULATORY PROVISIONS WITH ZONES:")
cursor.execute(f"""
    SELECT provision_type, zone, ref_number, 
           substr(provision_text, 1, 50) as text_snippet
    FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
    AND zone IS NOT NULL AND zone != ''
    ORDER BY RANDOM()
    LIMIT 10
""", REGULATORY_PROVISION_TYPES)

for i, (ptype, zone, ref, text) in enumerate(cursor.fetchall(), 1):
    print(f"   {i}. [{ptype}] Zone: {zone} | Ref: {ref}")
    print(f"      Text: {text}...")

# 6. Check if ANY regulatory provisions lack zones
print("\n6. REGULATORY PROVISIONS WITHOUT ZONES (should be empty):")
cursor.execute(f"""
    SELECT provision_type, ref_number, document_id
    FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
    AND (zone IS NULL OR zone = '')
    LIMIT 10
""", REGULATORY_PROVISION_TYPES)

missing = cursor.fetchall()
if not missing:
    print("   [SUCCESS] NONE FOUND - ALL REGULATORY PROVISIONS HAVE ZONES!")
else:
    print(f"   [FAILED] Found {len(missing)} provisions without zones:")
    for ptype, ref, doc in missing:
        print(f"      - {ptype}: {ref} from {doc}")

# 7. Zone distribution for regulatory provisions
print("\n7. ZONE DISTRIBUTION FOR REGULATORY PROVISIONS:")
cursor.execute(f"""
    SELECT zone, COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_type IN ({placeholders})
    AND zone IS NOT NULL
    GROUP BY zone
    ORDER BY count DESC
    LIMIT 10
""", REGULATORY_PROVISION_TYPES)

for zone, count in cursor.fetchall():
    percentage = (count / total_regulatory * 100) if total_regulatory > 0 else 0
    print(f"   {zone}: {count:,} provisions ({percentage:.1f}%)")

# 8. Verify specific critical types
print("\n8. VERIFICATION BY CRITICAL PROVISION TYPE:")
critical_types = ['height_limit', 'setback', 'fsr', 'provision_height', 'provision_setback']

for ptype in critical_types:
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN zone IS NOT NULL AND zone != '' THEN 1 END) as with_zone
        FROM regulatory_provisions
        WHERE provision_type = ?
    """, (ptype,))
    
    total, with_zone = cursor.fetchone()
    if total > 0:
        coverage = (with_zone / total * 100)
        status = "[OK]" if coverage == 100 else "[MISSING]"
        print(f"   {status} {ptype}: {with_zone}/{total} ({coverage:.1f}%)")

conn.close()

print("\n" + "=" * 70)
print("VERDICT:")
print("=" * 70)

if coverage >= 100.0:
    print("[PROVEN] 100% OF REGULATORY PROVISIONS HAVE ZONES")
    print(f"   {regulatory_with_zones:,} out of {total_regulatory:,} regulatory provisions have zones")
elif coverage >= 95.0:
    print(f"[ACCEPTABLE] {coverage:.1f}% OF REGULATORY PROVISIONS HAVE ZONES")
    print(f"   {regulatory_with_zones:,} out of {total_regulatory:,} regulatory provisions have zones")
else:
    print(f"[FAILED] ONLY {coverage:.1f}% OF REGULATORY PROVISIONS HAVE ZONES")
    print(f"   Missing zones for {regulatory_without_zones:,} regulatory provisions")

print("=" * 70)