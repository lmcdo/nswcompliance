#!/usr/bin/env python3
"""
Test 1: Verify Database Tables Have Expected Data
=================================================
Proves that development_controls and zone_setback_rules contain usable data
"""

import psycopg2
import sys

def test_development_controls_table():
    """Verify development_controls has extracted numeric values"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 1: DEVELOPMENT_CONTROLS TABLE")
    print("="*80)

    # Test 1.1: Table exists and has data
    cur.execute("SELECT COUNT(*) FROM development_controls;")
    total = cur.fetchone()[0]
    print(f"\n✓ Table exists with {total:,} rows")
    assert total > 4000, f"Expected >4000 rows, got {total}"

    # Test 1.2: Has required columns
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'development_controls'
        ORDER BY ordinal_position;
    """)
    columns = [r[0] for r in cur.fetchall()]
    required = ['control_type', 'value_numeric', 'unit', 'confidence_score', 'provision_id']

    print(f"\n✓ Has required columns: {', '.join(required)}")
    for col in required:
        assert col in columns, f"Missing column: {col}"

    # Test 1.3: Has data for R2 zone
    cur.execute("""
        SELECT COUNT(*)
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = 'R2';
    """)
    r2_count = cur.fetchone()[0]
    print(f"\n✓ Has {r2_count:,} controls for R2 zone")
    assert r2_count > 100, f"Expected >100 R2 controls, got {r2_count}"

    # Test 1.4: Has specific control types for R2
    cur.execute("""
        SELECT
            dc.control_type,
            COUNT(*) as count
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = 'R2'
          AND dc.control_type IN ('height', 'setback', 'parking', 'fsr')
        GROUP BY dc.control_type
        ORDER BY count DESC;
    """)

    print(f"\n✓ Control types for R2:")
    control_counts = {}
    for row in cur.fetchall():
        control_counts[row[0]] = row[1]
        print(f"  - {row[0]}: {row[1]} controls")

    assert 'height' in control_counts and control_counts['height'] > 50, "Need height controls"
    assert 'setback' in control_counts and control_counts['setback'] > 50, "Need setback controls"

    # Test 1.5: Has numeric values extracted
    cur.execute("""
        SELECT
            dc.control_type,
            dc.value_numeric,
            dc.unit,
            dc.confidence_score
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = 'R2'
          AND dc.control_type IN ('height', 'setback')
          AND dc.value_numeric IS NOT NULL
          AND dc.confidence_score::numeric > 0.75
        LIMIT 10;
    """)

    print(f"\n✓ Sample extracted values:")
    samples = cur.fetchall()
    assert len(samples) > 0, "No extracted values found"

    for row in samples[:5]:
        print(f"  - {row[0]}: {row[1]} {row[2]} (confidence: {row[3]})")

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 1 PASSED: development_controls table is ready")
    print("="*80)
    return True


def test_zone_setback_rules_table():
    """Verify zone_setback_rules has curated setbacks for R2"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 2: ZONE_SETBACK_RULES TABLE")
    print("="*80)

    # Test 2.1: Table exists
    cur.execute("SELECT COUNT(*) FROM zone_setback_rules;")
    total = cur.fetchone()[0]
    print(f"\n✓ Table exists with {total} rows")
    assert total > 0, "Table is empty"

    # Test 2.2: Has R2 rules
    cur.execute("""
        SELECT
            zone,
            boundary_type,
            base_value,
            unit,
            confidence,
            source_document
        FROM zone_setback_rules
        WHERE zone = 'R2'
        ORDER BY
            CASE boundary_type
                WHEN 'front' THEN 1
                WHEN 'side' THEN 2
                WHEN 'rear' THEN 3
                ELSE 4
            END;
    """)

    r2_rules = cur.fetchall()
    print(f"\n✓ Has {len(r2_rules)} setback rules for R2 zone:")

    assert len(r2_rules) >= 3, f"Expected at least 3 R2 rules (front/side/rear), got {len(r2_rules)}"

    boundary_types = set()
    for row in r2_rules:
        print(f"  - {row[1]}: {row[2]} {row[3]} (confidence: {row[4]}, source: {row[5][:50]}...)")
        boundary_types.add(row[1])

    # Test 2.3: Has front, side, rear setbacks
    print(f"\n✓ Boundary types present: {', '.join(sorted(boundary_types))}")
    assert 'front' in boundary_types, "Missing front setback"
    assert 'side' in boundary_types, "Missing side setback"
    assert 'rear' in boundary_types, "Missing rear setback"

    # Test 2.4: Has high confidence scores
    cur.execute("""
        SELECT AVG(confidence::numeric)
        FROM zone_setback_rules
        WHERE zone = 'R2';
    """)
    avg_confidence = cur.fetchone()[0]
    print(f"\n✓ Average confidence: {avg_confidence:.2f}")
    assert float(avg_confidence) > 0.90, f"Expected confidence >0.90, got {avg_confidence}"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 2 PASSED: zone_setback_rules table is ready")
    print("="*80)
    return True


def test_regulatory_provisions_linkage():
    """Verify regulatory_provisions links correctly to controls"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 3: REGULATORY_PROVISIONS LINKAGE")
    print("="*80)

    # Test 3.1: provision_id links work
    cur.execute("""
        SELECT COUNT(*)
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id;
    """)
    linked_count = cur.fetchone()[0]
    print(f"\n✓ {linked_count:,} controls successfully link to provisions")
    assert linked_count > 4000, f"Expected >4000 linked controls, got {linked_count}"

    # Test 3.2: Can get full text for controls
    cur.execute("""
        SELECT
            dc.control_type,
            dc.value_numeric,
            LEFT(rp.provision_text, 80) as text_preview,
            rp.zone
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = 'R2'
          AND dc.control_type = 'setback'
          AND dc.value_numeric IS NOT NULL
        LIMIT 5;
    """)

    print(f"\n✓ Sample linked controls with full text:")
    samples = cur.fetchall()
    assert len(samples) > 0, "No linked controls found"

    for row in samples:
        print(f"  - {row[0]} ({row[1]}): {row[2]}...")

    # Test 3.3: Zone field populated
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE zone IS NOT NULL;
    """)
    with_zone = cur.fetchone()[0]
    print(f"\n✓ {with_zone:,} provisions have zone populated")
    assert with_zone > 20000, f"Expected >20000 provisions with zone, got {with_zone}"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 3 PASSED: Linkage between tables works")
    print("="*80)
    return True


if __name__ == '__main__':
    try:
        test_development_controls_table()
        test_zone_setback_rules_table()
        test_regulatory_provisions_linkage()

        print("\n" + "="*80)
        print("✓ ALL DATABASE TESTS PASSED")
        print("="*80)
        print("\nDatabase is ready for API implementation")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)