"""
Add secondary_dwellings (granny flats) to LEP land use table

Based on Inner West LEP 2022 Clause 5.4:
Secondary dwellings are permitted in zones R2, R3, and E4
(E4 translates to RU5 Village, but Inner West has E4 as a transitional zone)
"""

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

# Zones where secondary dwellings are permitted (per LEP Clause 5.4)
secondary_dwelling_zones = [
    ('R2', 'Low Density Residential'),
    ('R3', 'Medium Density Residential'),
    ('E4', 'Environmental Living'),  # Legacy zone
]

lga = "Inner West"

print("Adding secondary_dwellings to LEP land use table...")

for zone_code, zone_name in secondary_dwelling_zones:
    cur.execute("""
        INSERT INTO lep_land_use_table
        (zone, zone_name, lga, development_type, permissibility, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (zone, lga, development_type) DO UPDATE
        SET notes = EXCLUDED.notes
    """, (
        zone_code,
        zone_name,
        lga,
        'secondary_dwellings',
        'permitted',
        'Permitted under LEP Clause 5.4 - subject to specific controls (max 60m2)'
    ))

    print(f"  Added secondary_dwellings to {zone_code} ({zone_name})")

conn.commit()

# Verify
cur.execute("""
    SELECT zone, zone_name, permissibility, notes
    FROM lep_land_use_table
    WHERE development_type = 'secondary_dwellings'
    ORDER BY zone
""")

print("\nVerification - secondary_dwellings now permitted in:")
for row in cur.fetchall():
    print(f"  {row[0]} ({row[1]}): {row[2]}")
    if row[3]:
        print(f"    Note: {row[3]}")

conn.close()

print("\n[OK] Secondary dwellings added successfully")
