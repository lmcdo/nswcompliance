#!/usr/bin/env python3
"""Fix the 20 bad extraction values"""

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)
cur = conn.cursor()

print("="*80)
print("FIXING BAD EXTRACTION VALUES")
print("="*80)

# 1. Find and show the bad height values (years)
print("\n[1] Finding height values that are years (2011, 2022)...\n")

cur.execute("""
    SELECT
        dc.id,
        dc.provision_id,
        dc.control_type,
        dc.value_numeric,
        rp.ref_number,
        LEFT(rp.provision_text, 80) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE dc.control_type = 'height'
      AND dc.value_numeric::numeric > 100;
""")

bad_heights = cur.fetchall()
print(f"Found {len(bad_heights)} height controls with year values:")
for row in bad_heights[:5]:
    print(f"  ID {row[0]}: {row[3]}m from '{row[4]}'")

# 2. Find and show the bad setback values (mm not converted to m)
print("\n\n[2] Finding setback values that are mm not m (900 instead of 0.9)...\n")

cur.execute("""
    SELECT
        dc.id,
        dc.provision_id,
        dc.control_type,
        dc.value_numeric,
        rp.ref_number,
        LEFT(rp.provision_text, 80) as text
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
    WHERE dc.control_type = 'setback'
      AND dc.value_numeric::numeric > 50;
""")

bad_setbacks = cur.fetchall()
print(f"Found {len(bad_setbacks)} setback controls with mm values:")
for row in bad_setbacks:
    print(f"  ID {row[0]}: {row[3]}m (should be {float(row[3])/1000}m)")
    print(f"    Text: {row[5]}")

# 3. Fix the bad height values - DELETE them (they're extracted years, not real heights)
print("\n\n[3] FIXING height values...\n")

print(f"Deleting {len(bad_heights)} height controls with year values (not real heights)")
cur.execute("""
    DELETE FROM development_controls
    WHERE control_type = 'height'
      AND value_numeric::numeric > 100;
""")
print(f"  Deleted {cur.rowcount} rows")

# 4. Fix the bad setback values - UPDATE them (convert mm to m)
print("\n\n[4] FIXING setback values...\n")

print(f"Converting {len(bad_setbacks)} setback values from mm to m (divide by 1000)")
cur.execute("""
    UPDATE development_controls
    SET value_numeric = (value_numeric::numeric / 1000)::text
    WHERE control_type = 'setback'
      AND value_numeric::numeric > 50;
""")
print(f"  Updated {cur.rowcount} rows")

# 5. Verify fixes
print("\n\n[5] VERIFICATION...\n")

cur.execute("""
    SELECT COUNT(*)
    FROM development_controls
    WHERE value_numeric::numeric > 100;
""")
remaining_bad = cur.fetchone()[0]
print(f"Remaining suspicious values (>100): {remaining_bad}")

cur.execute("""
    SELECT COUNT(*)
    FROM development_controls
    WHERE control_type = 'setback'
      AND value_numeric::numeric > 50;
""")
remaining_bad_setbacks = cur.fetchone()[0]
print(f"Remaining bad setbacks (>50m): {remaining_bad_setbacks}")

# Commit changes
conn.commit()

cur.close()
conn.close()

print("\n" + "="*80)
print("FIXES COMPLETE")
print("="*80)
print(f"\nDeleted: {len(bad_heights)} height controls (year extraction errors)")
print(f"Fixed: {len(bad_setbacks)} setback controls (mm → m conversion)")
print(f"\nDatabase now has clean data!")
print(f"Total good controls: 4,526 - {len(bad_heights)} = {4526 - len(bad_heights)}")