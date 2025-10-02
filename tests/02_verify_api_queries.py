#!/usr/bin/env python3
"""
Test 2: Verify API Query Results
================================
Proves that the new queries return correct, filtered data
"""

import psycopg2
import sys
import json

def test_controls_query_for_r2():
    """Test the new development_controls query returns correct results"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 1: CONTROLS QUERY FOR R2 + DWELLING_HOUSE")
    print("="*80)

    zone = 'R2'
    dev_type = 'dwelling_house'

    # Exact query that will be used in API
    query = """
        SELECT
            dc.control_type,
            dc.control_subtype,
            dc.value_numeric,
            dc.unit,
            dc.confidence_score,
            rp.id as provision_id,
            rp.provision_text,
            rp.ref_number,
            rp.section_header,
            rp.document_id,
            rp.zone
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = %s
          AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
          AND dc.confidence_score::numeric > 0.75
          AND dc.value_numeric IS NOT NULL
          AND (
              %s::text IS NULL
              OR rp.development_type = %s::text
              OR rp.development_type IS NULL
          )
        ORDER BY
            dc.confidence_score::numeric DESC,
            CASE dc.control_type
                WHEN 'height' THEN 1
                WHEN 'fsr' THEN 2
                WHEN 'setback' THEN 3
                WHEN 'parking' THEN 4
                ELSE 5
            END
        LIMIT 15
    """

    cur.execute(query, [zone, dev_type, dev_type])
    results = cur.fetchall()

    print(f"\n✓ Query returned {len(results)} controls")
    assert len(results) > 0, "Query returned no results"
    assert len(results) <= 15, f"Query should limit to 15, got {len(results)}"

    # Test result structure
    print(f"\n✓ Sample results:")
    control_types = {}
    for i, row in enumerate(results[:10]):
        control_type, subtype, value, unit, confidence, prov_id, text, ref, section, doc_id, zone = row

        print(f"\n  [{i+1}] {control_type} ({subtype or 'general'})")
        print(f"      Value: {value} {unit or ''}")
        print(f"      Confidence: {confidence}")
        print(f"      Provision ID: {prov_id}")
        print(f"      Document: {doc_id[:50]}...")

        control_types[control_type] = control_types.get(control_type, 0) + 1

        # Validate each result
        assert control_type in ['height', 'setback', 'parking', 'fsr', 'open_space'], f"Unexpected control type: {control_type}"
        assert value is not None, f"value_numeric is NULL for control {prov_id}"
        assert float(confidence) > 0.75, f"Confidence {confidence} is not >0.75"
        assert prov_id is not None, "provision_id is NULL"
        assert text is not None and len(text) > 0, "provision_text is empty"

    print(f"\n✓ Control type distribution:")
    for ctype, count in sorted(control_types.items()):
        print(f"  - {ctype}: {count}")

    # Test that we have essential control types
    assert 'height' in control_types or 'setback' in control_types, "Should have height or setback controls"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 1 PASSED: Controls query returns correct filtered data")
    print("="*80)
    return True


def test_setback_rules_query():
    """Test the zone_setback_rules query"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 2: SETBACK RULES QUERY FOR R2")
    print("="*80)

    zone = 'R2'

    # Exact query that will be used in API
    query = """
        SELECT
            zone,
            boundary_type as control_subtype,
            base_value as value_numeric,
            unit,
            confidence,
            source_clause as ref_number,
            source_document as document_id,
            'setback' as control_type
        FROM zone_setback_rules
        WHERE zone = %s
          AND confidence::numeric > 0.90
        ORDER BY
            CASE boundary_type
                WHEN 'front' THEN 1
                WHEN 'side' THEN 2
                WHEN 'rear' THEN 3
                ELSE 4
            END
    """

    cur.execute(query, [zone])
    results = cur.fetchall()

    print(f"\n✓ Query returned {len(results)} setback rules")
    assert len(results) >= 3, f"Expected at least 3 rules (front/side/rear), got {len(results)}"

    print(f"\n✓ Setback rules:")
    boundary_types = set()
    for row in results:
        zone, subtype, value, unit, confidence, ref, doc_id, control_type = row
        print(f"  - {subtype}: {value} {unit} (confidence: {confidence})")
        print(f"    Source: {doc_id[:60]}...")

        boundary_types.add(subtype)

        # Validate
        assert control_type == 'setback', f"control_type should be 'setback', got {control_type}"
        assert value is not None, f"value_numeric is NULL for {subtype}"
        assert float(confidence) > 0.90, f"Confidence {confidence} is not >0.90"

    print(f"\n✓ Boundary types: {', '.join(sorted(boundary_types))}")
    assert 'front' in boundary_types, "Missing front setback"
    assert 'side' in boundary_types, "Missing side setback"
    assert 'rear' in boundary_types, "Missing rear setback"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 2 PASSED: Setback rules query returns complete data")
    print("="*80)
    return True


def test_combined_results():
    """Test combining both queries as API will do"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 3: COMBINED QUERY RESULTS")
    print("="*80)

    zone = 'R2'
    dev_type = 'dwelling_house'

    # Query 1: Controls
    controls_query = """
        SELECT
            dc.control_type,
            dc.control_subtype,
            dc.value_numeric,
            dc.unit,
            dc.confidence_score as confidence,
            rp.id as provision_id,
            rp.provision_text,
            rp.document_id
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = %s
          AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
          AND dc.confidence_score::numeric > 0.75
          AND dc.value_numeric IS NOT NULL
        ORDER BY dc.confidence_score::numeric DESC
        LIMIT 15
    """

    cur.execute(controls_query, [zone])
    controls = cur.fetchall()

    # Query 2: Setback rules
    setback_query = """
        SELECT
            'setback' as control_type,
            boundary_type as control_subtype,
            base_value as value_numeric,
            unit,
            confidence,
            NULL as provision_id,
            'Curated setback rule' as provision_text,
            source_document as document_id
        FROM zone_setback_rules
        WHERE zone = %s
          AND confidence::numeric > 0.90
    """

    cur.execute(setback_query, [zone])
    setbacks = cur.fetchall()

    # Combine
    all_controls = controls + setbacks

    print(f"\n✓ Combined results: {len(all_controls)} total controls")
    print(f"  - From development_controls: {len(controls)}")
    print(f"  - From zone_setback_rules: {len(setbacks)}")

    # Categorize by type
    by_type = {}
    for row in all_controls:
        control_type = row[0]
        by_type[control_type] = by_type.get(control_type, 0) + 1

    print(f"\n✓ Controls by type:")
    for ctype, count in sorted(by_type.items()):
        print(f"  - {ctype}: {count}")

    # Test we have building envelope controls
    building_envelope_types = ['height', 'fsr', 'setback']
    envelope_count = sum(by_type.get(t, 0) for t in building_envelope_types)

    print(f"\n✓ Building envelope controls: {envelope_count}")
    assert envelope_count >= 5, f"Expected at least 5 building envelope controls, got {envelope_count}"

    # Show sample
    print(f"\n✓ Sample combined results:")
    for i, row in enumerate(all_controls[:8]):
        control_type, subtype, value, unit, confidence, prov_id, text, doc_id = row
        print(f"  [{i+1}] {control_type} ({subtype or 'general'}): {value} {unit or ''} (conf: {confidence})")

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 3 PASSED: Combined queries provide comprehensive data")
    print("="*80)
    return True


if __name__ == '__main__':
    try:
        test_controls_query_for_r2()
        test_setback_rules_query()
        test_combined_results()

        print("\n" + "="*80)
        print("✓ ALL QUERY TESTS PASSED")
        print("="*80)
        print("\nQueries will return correct, filtered data for API")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)