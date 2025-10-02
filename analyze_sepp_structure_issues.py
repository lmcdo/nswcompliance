from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== DATABASE STRUCTURE ANALYSIS FOR SEPP RELATIONSHIPS ===\n")

# Issue 1: Planning Portal identifies "Transport & Infrastructure Amendment 2022"
# But database has provisions in "Planning Systems SEPP 2021"
print("ISSUE 1: THERMAL ENERGY WASTE - SEPP MISMATCH\n")
print("Planning Portal says: Transport and Infrastructure SEPP 2021")
print("                      + Amendment (Thermal Energy from Waste) 2022")
print("Database has:         Planning Systems SEPP 2021\n")

cur.execute("""
    SELECT id, ref_number, document_id, provision_text
    FROM regulatory_provisions
    WHERE id IN (18945, 19101, 19195)
""")
rows = cur.fetchall()
for row in rows:
    print(f"ID {row[0]}: {row[2]}")
    print(f"  Ref: {row[1]}")
    print(f"  Text: {row[3][:150]}...\n")

print("PROBLEM: Provisions are in Planning Systems SEPP, not Transport & Infrastructure SEPP")
print("SOLUTION: Need 'sepp_amendments' table to track that Planning Systems provisions")
print("          were moved/referenced by Transport & Infrastructure Amendment 2022\n")

print("="*80 + "\n")

# Issue 2: SEPP maps not linked to provisions
print("ISSUE 2: SEPP MAPS NOT LINKED TO PROVISIONS\n")

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE '%map%'
    ORDER BY table_name
""")
map_tables = cur.fetchall()
print(f"Map-related tables: {[t[0] for t in map_tables]}\n")

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name LIKE '%sepp%'
    ORDER BY table_name
""")
sepp_tables = cur.fetchall()
print(f"SEPP-related tables: {[t[0] for t in sepp_tables]}\n")

print("PROBLEM: No table linking SEPP map detections to provisions")
print("SOLUTION: Need 'sepp_maps' table with map_type (TEW, BAL, CLM, etc.) linked to provisions\n")

print("="*80 + "\n")

# Issue 3: Climate zones are stored as text, not structured data
print("ISSUE 3: CLIMATE ZONES NOT STRUCTURED\n")

cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%Sustainable_Buildings%'
    AND provision_text ILIKE '%climate zone%'
    LIMIT 3
""")
rows = cur.fetchall()
for row in rows:
    print(f"ID {row[0]}: {row[1]}")
    print(f"  {row[2][:200]}...\n")

print("PROBLEM: Climate zones are just text, not linked to geographic areas")
print("SOLUTION: Need 'climate_zones' table with zone_id, zone_name, geographic boundaries\n")

print("="*80 + "\n")

# Issue 4: Water use standards not linked to geographic areas
print("ISSUE 4: WATER USE STANDARDS NOT GEOGRAPHIC\n")

cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE id IN (6130, 6131, 6174)
""")
rows = cur.fetchall()
for row in rows:
    print(f"ID {row[0]}: {row[1]}")
    print(f"  {row[2][:200]}...\n")

print("PROBLEM: Water Use Map references (Area A, Area B, 40%) not linked to property locations")
print("SOLUTION: Need 'water_use_zones' table with percentage standards linked to LGA/postcode\n")

print("="*80 + "\n")

# Check current schema
print("CURRENT DATABASE SCHEMA\n")

cur.execute("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
cols = cur.fetchall()
print("regulatory_provisions columns:")
for col in cols:
    print(f"  - {col[1]}: {col[2]}")

print("\n" + "="*80 + "\n")

print("RECOMMENDED SCHEMA CHANGES:\n")
print("""
1. CREATE TABLE sepp_amendments (
    id SERIAL PRIMARY KEY,
    amendment_name TEXT,
    base_sepp_id INTEGER,  -- References the SEPP being amended
    amendment_date DATE,
    commenced_date DATE,
    amendment_type TEXT,  -- 'adds', 'modifies', 'repeals'
    affected_provision_ids INTEGER[],  -- Array of provision IDs affected
    amendment_document_id TEXT
);

2. CREATE TABLE sepp_maps (
    id SERIAL PRIMARY KEY,
    map_name TEXT,
    map_type TEXT,  -- 'TEW', 'BAL', 'CLM', 'HER', etc.
    sepp_document_id TEXT,
    provision_ids INTEGER[],  -- Provisions that reference this map
    geometry_data JSONB,  -- Geographic boundaries if available
    applies_to_lgas TEXT[]  -- LGAs covered by this map
);

3. CREATE TABLE climate_zones (
    id SERIAL PRIMARY KEY,
    zone_number INTEGER,  -- e.g. 2049, 5
    zone_name TEXT,  -- e.g. 'INNER WEST'
    sepp_map_id INTEGER REFERENCES sepp_maps(id),
    lgas TEXT[],
    postcodes TEXT[],
    provisions_by_zone JSONB  -- Standards that vary by zone
);

4. CREATE TABLE water_use_zones (
    id SERIAL PRIMARY KEY,
    area_designation TEXT,  -- 'Area A', 'Area B'
    reduction_percentage INTEGER,  -- 0, 10, 20, 30, 40
    lgas TEXT[],
    postcodes TEXT[],
    provision_id INTEGER REFERENCES regulatory_provisions(id)
);

5. CREATE TABLE sepp_metadata (
    id SERIAL PRIMARY KEY,
    sepp_name TEXT UNIQUE,
    document_id TEXT,
    commenced_date DATE,
    current_version_date DATE,
    epi_number TEXT,  -- e.g. '2021-732'
    supersedes TEXT,  -- Previous SEPP name
    amendments JSONB  -- Array of amendment references
);

6. ALTER TABLE regulatory_provisions ADD COLUMNS:
    - sepp_metadata_id INTEGER REFERENCES sepp_metadata(id)
    - map_references TEXT[]  -- Map types this provision references
    - geographic_scope TEXT  -- 'Greater Sydney', 'NSW-wide', 'LGA-specific'
    - applies_to_zones TEXT[]  -- Climate zones this provision applies to
""")

c.close()