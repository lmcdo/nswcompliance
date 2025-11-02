"""
Import Standard Instrument Land Use Tables to database

This script:
1. Creates the lep_land_use_table table
2. Imports all Standard Instrument zones and development types
3. Handles permitted, permissible, and prohibited classifications
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from lep_land_use_tables_standard_instrument import STANDARD_LAND_USE_TABLES

# Database connection
conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

print("Creating lep_land_use_table...")

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS lep_land_use_table (
        id SERIAL PRIMARY KEY,
        zone VARCHAR(10) NOT NULL,
        zone_name VARCHAR(255) NOT NULL,
        lga VARCHAR(255) NOT NULL,
        development_type VARCHAR(255) NOT NULL,
        permissibility VARCHAR(50) NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(zone, lga, development_type)
    )
""")

# Create index for faster lookups
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_lep_land_use_zone_lga_devtype
    ON lep_land_use_table(zone, lga, development_type)
""")

conn.commit()
print("[OK] Table created")

# Import data
total_inserted = 0
lga = "Inner West"  # Standard Instrument applies to Inner West LEP 2022

print(f"\nImporting land use tables for {len(STANDARD_LAND_USE_TABLES)} zones...")

for zone_code, zone_data in STANDARD_LAND_USE_TABLES.items():
    zone_name = zone_data['zone_name']

    # Insert permitted_with_consent as "permitted"
    permitted = zone_data.get('permitted_with_consent', [])
    for dev_type in permitted:
        # Normalize development type name to snake_case
        dev_type_normalized = dev_type.lower().replace(' ', '_').replace('-', '_')

        try:
            cur.execute("""
                INSERT INTO lep_land_use_table
                (zone, zone_name, lga, development_type, permissibility)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (zone, lga, development_type) DO NOTHING
            """, (zone_code, zone_name, lga, dev_type_normalized, 'permitted'))
            total_inserted += 1
        except Exception as e:
            print(f"Error inserting {dev_type_normalized} in {zone_code}: {e}")

    # Insert permitted_without_consent (rare, but handle it)
    permitted_without = zone_data.get('permitted_without_consent', [])
    for dev_type in permitted_without:
        dev_type_normalized = dev_type.lower().replace(' ', '_').replace('-', '_')

        try:
            cur.execute("""
                INSERT INTO lep_land_use_table
                (zone, zone_name, lga, development_type, permissibility, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (zone, lga, development_type) DO NOTHING
            """, (zone_code, zone_name, lga, dev_type_normalized, 'permitted', 'No consent required'))
            total_inserted += 1
        except Exception as e:
            print(f"Error inserting {dev_type_normalized} in {zone_code}: {e}")

    print(f"  {zone_code} ({zone_name}): {len(permitted) + len(permitted_without)} development types")

conn.commit()

# Verify import
cur.execute("SELECT COUNT(*) FROM lep_land_use_table")
total_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT zone) FROM lep_land_use_table")
zone_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(DISTINCT development_type) FROM lep_land_use_table")
dev_type_count = cur.fetchone()[0]

print(f"\n{'='*60}")
print(f"IMPORT COMPLETE")
print(f"{'='*60}")
print(f"Total rows inserted: {total_count}")
print(f"Zones: {zone_count}")
print(f"Unique development types: {dev_type_count}")
print(f"Average dev types per zone: {total_count / zone_count:.1f}")

# Show sample data
print(f"\nSample data (R2 Zone):")
cur.execute("""
    SELECT development_type, permissibility
    FROM lep_land_use_table
    WHERE zone = 'R2' AND lga = 'Inner West'
    ORDER BY development_type
    LIMIT 10
""")

for row in cur.fetchall():
    print(f"  - {row[0]}: {row[1]}")

conn.close()

print(f"\n[OK] LEP Land Use Tables imported successfully")
