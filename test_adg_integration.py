#!/usr/bin/env python3
"""
Test ADG Integration - Verify database and API
Uses safe db wrapper as per .claude guidelines
"""
import sys
sys.path.append('venv_linux/lib/python3.11/site-packages')
from db_safety_wrapper import get_safe_connection

print("=" * 80)
print("TESTING ADG INTEGRATION")
print("=" * 80)

# Test 1: Verify database records
print("\n[TEST 1] Verifying ADG standards in database...")
try:
    with get_safe_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ref_number,
                    boundary_type,
                    building_element,
                    site_condition[1] as height_category,
                    setback_meters,
                    development_type
                FROM setback_rules
                WHERE ref_number LIKE 'ADG 3F-1%'
                ORDER BY
                    CASE
                        WHEN site_condition[1] = 'building_height_up_to_12m' THEN 1
                        WHEN site_condition[1] = 'building_height_12m_to_25m' THEN 2
                        WHEN site_condition[1] = 'building_height_over_25m' THEN 3
                    END,
                    boundary_type,
                    ref_number;
            """)

            records = cur.fetchall()

            if len(records) == 12:
                print(f"[PASS] Found {len(records)} ADG standards (expected 12)")
                print("\n   Summary:")
                print("   Height Category            | Boundary | Ref Number              | Setback")
                print("   " + "-" * 75)
                for row in records:
                    ref, boundary, element, height, setback, dev_types = row
                    height_label = height.replace('building_height_', '').replace('_', ' ')
                    print(f"   {height_label:25s} | {boundary:8s} | {ref:23s} | {setback}m")
            else:
                print(f"[FAIL] Expected 12 records, found {len(records)}")

except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: Verify height category logic
print("\n[TEST 2] Testing height category queries...")
test_cases = [
    (10, 'building_height_up_to_12m', '6.0m'),
    (15, 'building_height_12m_to_25m', '9.0m'),
    (30, 'building_height_over_25m', '12.0m')
]

for height, expected_category, expected_setback in test_cases:
    try:
        with get_safe_connection() as conn:
            with conn.cursor() as cur:
                # Simulate API logic
                if height <= 12:
                    category = 'building_height_up_to_12m'
                elif height <= 25:
                    category = 'building_height_12m_to_25m'
                else:
                    category = 'building_height_over_25m'

                cur.execute("""
                    SELECT setback_meters
                    FROM setback_rules
                    WHERE ref_number = 'ADG 3F-1'
                    AND boundary_type = 'side'
                    AND %s = ANY(site_condition)
                    LIMIT 1;
                """, (category,))

                result = cur.fetchone()

                if result and float(result[0]) == float(expected_setback.replace('m', '')):
                    print(f"   [OK] {height}m -> {category.replace('building_height_', '')} -> {expected_setback}")
                else:
                    print(f"   [FAIL] {height}m -> Expected {expected_setback}, got {result[0] if result else 'None'}")

    except Exception as e:
        print(f"   [ERROR] for {height}m: {e}")

# Test 3: Verify development type filtering
print("\n[TEST 3] Testing development type filtering...")
try:
    with get_safe_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT unnest(development_type) as dev_type
                FROM setback_rules
                WHERE ref_number LIKE 'ADG 3F-1%'
                ORDER BY dev_type;
            """)

            dev_types = [row[0] for row in cur.fetchall()]
            expected_types = ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing']

            if set(dev_types) == set(expected_types):
                print(f"   [OK] Development types correct: {', '.join(dev_types)}")
            else:
                print(f"   [FAIL] Expected {expected_types}, got {dev_types}")

except Exception as e:
    print(f"   [ERROR] {e}")

# Test 4: Verify source citations
print("\n[TEST 4] Verifying source citations...")
try:
    with get_safe_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    document_name,
                    source_text,
                    manual_verified,
                    extraction_confidence
                FROM setback_rules
                WHERE ref_number = 'ADG 3F-1'
                LIMIT 1;
            """)

            result = cur.fetchone()

            if result:
                doc_name, source_text, manual_verified, confidence = result
                print(f"   [OK] Document: {doc_name}")
                print(f"   [OK] Manual verified: {manual_verified}")
                print(f"   [OK] Confidence: {confidence}")
                if 'SEPP (Housing) 2021' in (source_text or ''):
                    print(f"   [OK] Source cites SEPP (Housing) 2021")
                else:
                    print(f"   [WARN] Source missing SEPP citation")
            else:
                print(f"   [FAIL] No source data found")

except Exception as e:
    print(f"   [ERROR] {e}")

print("\n" + "=" * 80)
print("ADG INTEGRATION TEST COMPLETE")
print("=" * 80)
