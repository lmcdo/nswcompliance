import pytest
pytestmark = pytest.mark.stale

"""Test the actual queries being run for Ashfield"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:Onlyme123!@127.0.0.1:5432/nsw_planning')
cur = conn.cursor()

print("=" * 70)
print("TESTING ASHFIELD QUERY PATHS")
print("=" * 70)

# Test parameters as they come from the API
queryLGA = 'Inner West'
zoneAliases = ['R2']  # Common test case
developmentType = 'dwelling_house'
councilForQuery = 'Ashfield'

# Test 1: Current Ashfield residential query (with zone + devtype filtering)
print("\n--- Test 1: Current residential query (zone + devtype) ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND dgr.applicable_zones && %s::text[]
    AND %s = ANY(dgr.development_types)
    AND dgr.former_council = %s
""", (queryLGA, zoneAliases, developmentType, councilForQuery))
print(f"Count with zone+devtype filter: {cur.fetchone()[0]}")

# Test 2: Without zone filter (only devtype)
print("\n--- Test 2: Without zone filter (devtype only) ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND %s = ANY(dgr.development_types)
    AND dgr.former_council = %s
""", (queryLGA, developmentType, councilForQuery))
print(f"Count with devtype only: {cur.fetchone()[0]}")

# Test 3: Without devtype filter (zone only)
print("\n--- Test 3: Without devtype filter (zone only) ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND dgr.applicable_zones && %s::text[]
    AND dgr.former_council = %s
""", (queryLGA, zoneAliases, councilForQuery))
print(f"Count with zone only: {cur.fetchone()[0]}")

# Test 4: No zone/devtype filter
print("\n--- Test 4: No zone/devtype filter ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND dgr.former_council = %s
""", (queryLGA, councilForQuery))
print(f"Count with no filters: {cur.fetchone()[0]}")

# Test 5: Check what dwelling_house requirements look like
print("\n--- Test 5: Sample dwelling_house requirements ---")
cur.execute("""
    SELECT id, category, LEFT(requirement_text, 60), applicable_zones
    FROM dcp_general_requirements
    WHERE former_council = 'Ashfield'
    AND 'dwelling_house' = ANY(development_types)
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"  id={row[0]}, cat={row[1]}, zones={row[3]}")

# Test 6: Check if zone filter issue is due to empty arrays
print("\n--- Test 6: Zone status for dwelling_house ---")
cur.execute("""
    SELECT
        CASE WHEN applicable_zones IS NULL THEN 'NULL'
             WHEN array_length(applicable_zones, 1) IS NULL THEN 'EMPTY'
             ELSE 'HAS_VALUES' END as status,
        COUNT(*)
    FROM dcp_general_requirements
    WHERE former_council = 'Ashfield'
    AND 'dwelling_house' = ANY(development_types)
    GROUP BY 1
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Test 7: Proposed fix - zone filter that allows empty arrays
print("\n--- Test 7: Proposed fix (zone filter OR empty zones) ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND (dgr.applicable_zones && %s::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
    AND %s = ANY(dgr.development_types)
    AND dgr.former_council = %s
""", (queryLGA, zoneAliases, developmentType, councilForQuery))
print(f"Count with relaxed zone filter: {cur.fetchone()[0]}")

# Test 8: Commercial zone test
print("\n--- Test 8: Commercial (E1/B1/B2) zone test ---")
zoneAliases_commercial = ['E1', 'B1', 'B2']
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND dgr.applicable_zones && %s::text[]
    AND dgr.former_council = %s
""", (queryLGA, zoneAliases_commercial, councilForQuery))
print(f"Commercial zones strict: {cur.fetchone()[0]}")

cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND (dgr.applicable_zones && %s::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
    AND dgr.former_council = %s
""", (queryLGA, zoneAliases_commercial, councilForQuery))
print(f"Commercial zones relaxed: {cur.fetchone()[0]}")

conn.close()
