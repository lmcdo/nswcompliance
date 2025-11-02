"""
Test permissibility query logic

Simulates what the API endpoint will do:
1. Given an address and development type
2. Get zone from property
3. Query LEP land use table
4. Return permissibility result
"""

import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)

cur = conn.cursor()

# Test scenarios
test_cases = [
    {
        "address": "181 Addison Road, Ashfield",
        "zone": "R2",
        "dev_type": "secondary_dwellings",
        "expected": "permitted"
    },
    {
        "address": "181 Addison Road, Ashfield",
        "zone": "R2",
        "dev_type": "dual_occupancies",
        "expected": "permitted"
    },
    {
        "address": "181 Addison Road, Ashfield",
        "zone": "R2",
        "dev_type": "shop_top_housing",
        "expected": "prohibited"
    },
    {
        "address": "1 Marrickville Road, Marrickville (B2 zone)",
        "zone": "B2",
        "dev_type": "shop_top_housing",
        "expected": "permitted"
    },
]

print("PERMISSIBILITY QUERY TESTS")
print("=" * 80)

for test in test_cases:
    print(f"\nTest: {test['address']}")
    print(f"  Zone: {test['zone']}")
    print(f"  Development Type: {test['dev_type']}")

    # Query LEP land use table
    cur.execute("""
        SELECT permissibility, zone_name, notes
        FROM lep_land_use_table
        WHERE zone = %s
          AND lga = %s
          AND development_type = %s
    """, (test['zone'], 'Inner West', test['dev_type']))

    result = cur.fetchone()

    if result:
        permissibility = result[0]
        zone_name = result[1]
        notes = result[2]

        print(f"  Result: {permissibility.upper()}")
        print(f"  Zone Name: {zone_name}")
        if notes:
            print(f"  Notes: {notes}")

        if permissibility == test['expected']:
            print(f"  [PASS] Matches expected: {test['expected']}")
        else:
            print(f"  [FAIL] Expected {test['expected']}, got {permissibility}")
    else:
        print(f"  Result: PROHIBITED (not in land use table)")
        if test['expected'] == 'prohibited':
            print(f"  [PASS] Matches expected: prohibited")
        else:
            print(f"  [FAIL] Expected {test['expected']}, got prohibited")

    # If prohibited, find alternatives
    if not result or result[0] == 'prohibited':
        cur.execute("""
            SELECT development_type
            FROM lep_land_use_table
            WHERE zone = %s
              AND lga = %s
              AND permissibility IN ('permitted', 'permissible')
            ORDER BY development_type
            LIMIT 5
        """, (test['zone'], 'Inner West'))

        alternatives = [row[0] for row in cur.fetchall()]
        if alternatives:
            print(f"  Alternative options in {test['zone']}: {', '.join(alternatives[:3])}, ...")

conn.close()

print("\n" + "=" * 80)
print("[OK] Permissibility query tests complete")
