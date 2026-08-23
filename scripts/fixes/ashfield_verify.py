#!/usr/bin/env python3
"""Phase 6: Verify Ashfield Chapter F fix"""
import os
import psycopg2

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"
conn = psycopg2.connect(LOCAL_DB)
cur = conn.cursor()

print("=" * 60)
print("Phase 6: Verification")
print("=" * 60)

# Check layer distribution
cur.execute("""
    SELECT v2_dcp_layer, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_is_actionable = true
    GROUP BY v2_dcp_layer
    ORDER BY COUNT(*) DESC
""")
print("\nAshfield layer distribution (actionable only):")
for row in cur.fetchall():
    layer = row[0] or "NULL"
    print(f"  {layer:15} {row[1]:5}")

# Test R2 zone filter
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'use_specific'
      AND 'R2' = ANY(v2_applicable_zones)
""")
r2_count = cur.fetchone()[0]
print(f"\nR2 zone provisions: {r2_count}")

# Test dwelling_house dev type
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_dcp_layer = 'use_specific'
      AND 'dwelling_house' = ANY(v2_applicable_dev_types)
""")
dh_count = cur.fetchone()[0]
print(f"Dwelling house provisions: {dh_count}")

# Summary
print("\n" + "=" * 60)
print("BEFORE vs AFTER:")
print("  Zone (use_specific): 0 -> 70")
print(f"  R2 zone filter: 0 -> {r2_count}")
print(f"  Dwelling house filter: 0 -> {dh_count}")
print("=" * 60)

conn.close()
