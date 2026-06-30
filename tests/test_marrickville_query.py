import pytest
pytestmark = pytest.mark.stale

"""Test the actual queries being run for Marrickville"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres@127.0.0.1:5432/nsw_planning')
cur = conn.cursor()

print("=" * 70)
print("TESTING MARRICKVILLE QUERY PATHS")
print("=" * 70)

# Test parameters as they come from the API
queryLGA = 'Inner West'
councilForQuery = 'Marrickville'

# Test 1: Current Marrickville query
print("\n--- Test 1: Current Marrickville query ---")
cur.execute("""
    SELECT COUNT(*)
    FROM dcp_general_requirements dgr
    WHERE dgr.lga = %s
    AND dgr.former_council = %s
""", (queryLGA, councilForQuery))
print(f"Count: {cur.fetchone()[0]}")

# Test 2: Check case sensitivity
print("\n--- Test 2: Case variations ---")
for fc in ['Marrickville', 'marrickville', 'MARRICKVILLE']:
    cur.execute("""
        SELECT COUNT(*)
        FROM dcp_general_requirements dgr
        WHERE dgr.lga = %s
        AND dgr.former_council = %s
    """, (queryLGA, fc))
    print(f"  '{fc}': {cur.fetchone()[0]}")

# Test 3: Check if dcp_general_provisions returns anything for Marrickville
print("\n--- Test 3: dcp_general_provisions (used first in code) ---")
cur.execute("""
    SELECT COUNT(*) FROM dcp_general_provisions WHERE lga = 'Inner West'
""")
print(f"dcp_general_provisions count (lga='Inner West'): {cur.fetchone()[0]}")

# This is the issue - provisions table has no former_council, so Marrickville
# gets ALL Inner West provisions (1172), then skips requirements query

# Test 4: What categories does Marrickville have?
print("\n--- Test 4: Marrickville categories ---")
cur.execute("""
    SELECT category, COUNT(*)
    FROM dcp_general_requirements
    WHERE former_council = 'Marrickville'
    GROUP BY category
    ORDER BY 2 DESC
""")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

conn.close()
