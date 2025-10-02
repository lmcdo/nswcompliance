#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("DATABASE MAP DATA ANALYSIS")
print("=" * 80)

# Check for tables that might contain map/spatial data
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name ILIKE '%map%'
    ORDER BY table_name
""")

print("\n=== Tables with 'map' in name ===")
map_tables = cur.fetchall()
if map_tables:
    for table in map_tables:
        print(f"  {table[0]}")
else:
    print("  None found")

# Check for spatial/geometry columns
cur.execute("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND (data_type ILIKE '%geometry%' OR data_type ILIKE '%geography%')
    ORDER BY table_name
""")

print("\n=== Spatial/Geometry columns ===")
spatial = cur.fetchall()
if spatial:
    for table, col, dtype in spatial:
        print(f"  {table}.{col} ({dtype})")
else:
    print("  None found - no PostGIS spatial data")

# Check if we have SEPP map references in text
cur.execute("""
    SELECT document_id, COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_text ILIKE '%climate zone%map%'
       OR provision_text ILIKE '%basix%map%'
       OR provision_text ILIKE '%water use%map%'
    GROUP BY document_id
    ORDER BY count DESC
    LIMIT 5
""")

print("\n=== Documents with map references in text ===")
for doc, count in cur.fetchall():
    sepp_name = doc.split('___')[0].replace('State_Environmental_Planning_Policy_', 'SEPP ').replace('_', ' ')
    print(f"  {count:3} provisions - {sepp_name}")

# Check what Climate Zone data we have
cur.execute("""
    SELECT provision_text
    FROM regulatory_provisions
    WHERE provision_text ILIKE '%climate zone means%'
    LIMIT 1
""")

print("\n=== Sample Climate Zone definition text ===")
result = cur.fetchone()
if result:
    print(result[0][:500] + "...")
else:
    print("  Not found")

print("\n\n=== SUMMARY ===")
print("""
What we HAVE:
- ✓ SEPP provision text that REFERENCES maps
  (e.g., "climate zone means the climate zone shown on [Map Name]")
- ✓ Text descriptions of map requirements
- ✓ Rules based on map values

What we DON'T HAVE:
- ✗ Actual GIS/spatial map boundaries
- ✗ Map tiles or raster data
- ✗ Polygon/geometry data for climate zones, BASIX areas, etc.

How it works:
1. User searches address (e.g., "30 Illawarra Road, Marrickville")
2. NSW Planning Portal API returns map values for that property
   → "Climate Zone: Class 8" (from BASIX Climate Zones map)
   → "Water Use: 40%" (from Water Use map)
3. We display these values from Planning API
4. We show SEPP provision text that explains what these values mean
5. We do NOT independently verify/calculate map values

Architecture:
- Planning Portal = Authoritative source for map data per property
- Our database = Reference text explaining what map values mean
- We TRUST Planning Portal's map results, don't duplicate spatial data
""")

conn.close()
