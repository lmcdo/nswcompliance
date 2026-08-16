#!/usr/bin/env python3
"""Fix Marrickville zone tagging - simplified"""

import psycopg2

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': 'eDDIYq8ottiaO9ll',
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'port': 5432
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("FIX MARRICKVILLE ZONE TAGGING")
print("=" * 80)
print()

# Part 4.1 -> R2
print("Part 4.1 -> ['R2']")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_applicable_zones = ARRAY['R2']
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part = 'Part 4.1'
      AND v2_is_actionable = true;
""")
print(f"  Updated {cur.rowcount} provisions")
print()

# Part 4.2 -> R3, R4
print("Part 4.2 -> ['R3', 'R4']")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_applicable_zones = ARRAY['R3', 'R4']
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part = 'Part 4.2'
      AND v2_is_actionable = true;
""")
print(f"  Updated {cur.rowcount} provisions")
print()

# Part 5 -> B zones
print("Part 5 -> ['B1', 'B2', 'B4', 'B5', 'B6']")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_applicable_zones = ARRAY['B1', 'B2', 'B4', 'B5', 'B6']
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part = 'Part 5'
      AND v2_is_actionable = true;
""")
print(f"  Updated {cur.rowcount} provisions")
print()

# Part 6 -> IN zones
print("Part 6 -> ['IN1', 'IN2', 'IN3']")
cur.execute("""
    UPDATE regulatory_provisions
    SET v2_applicable_zones = ARRAY['IN1', 'IN2', 'IN3']
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part = 'Part 6'
      AND v2_is_actionable = true;
""")
print(f"  Updated {cur.rowcount} provisions")
print()

conn.commit()

# Verify
print("Verification:")
print("-" * 80)
cur.execute("""
    SELECT v2_dcp_part, v2_applicable_zones, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part IN ('Part 4.1', 'Part 4.2', 'Part 5', 'Part 6')
      AND v2_is_actionable = true
    GROUP BY v2_dcp_part, v2_applicable_zones
    ORDER BY v2_dcp_part;
""")

for row in cur.fetchall():
    print(f"  {row[0]:15s}: {row[2]:3d} provisions -> {row[1]}")

print()
print("=" * 80)
print("[COMPLETE]")
print("=" * 80)

cur.close()
conn.close()
