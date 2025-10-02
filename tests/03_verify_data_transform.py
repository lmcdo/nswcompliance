#!/usr/bin/env python3
"""
Test 3: Verify Data Transformation
==================================
Proves that controls transform correctly into UI constraint format
"""

import psycopg2
import sys
from typing import Dict, List, Any

def simulate_transform(control: tuple) -> Dict[str, Any]:
    """
    Simulate the TypeScript transform function
    This is what the API will do to each control
    """

    control_type, control_subtype, value_numeric, unit, confidence, provision_id, provision_text, ref_number, section_header, document_id, zone = control

    # Map control types to UI types
    type_mapping = {
        'height': 'height',
        'fsr': 'fsr',
        'setback': 'setback',
        'parking': 'special',
        'open_space': 'special'
    }

    ui_type = type_mapping.get(control_type, 'environmental')

    # Extract document name
    doc_name = document_id.split('___')[0].replace('_', ' ') if document_id else 'Unknown'

    # Infer authority level
    doc_lower = (document_id or '').lower()
    if 'sepp' in doc_lower or 'state_environmental' in doc_lower:
        authority = 'SEPP'
    elif 'lep' in doc_lower or 'local_environmental' in doc_lower:
        authority = 'LEP'
    else:
        authority = 'DCP'

    return {
        'type': ui_type,
        'value': float(value_numeric) if value_numeric else 'See provision',
        'unit': unit,
        'source': {
            'clause': ref_number or 'N/A',
            'document': doc_name,
            'authority_level': authority
        },
        'provision_id': provision_id,
        'full_text': provision_text[:100] + '...' if provision_text and len(provision_text) > 100 else provision_text,
        'confidence': float(confidence) if confidence else None,
        'subtype': control_subtype
    }


def test_transform_controls():
    """Test transforming development_controls results"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 1: TRANSFORM DEVELOPMENT_CONTROLS")
    print("="*80)

    # Get sample controls
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
        WHERE rp.zone = 'R2'
          AND dc.control_type IN ('height', 'setback', 'parking')
          AND dc.value_numeric IS NOT NULL
          AND dc.confidence_score::numeric > 0.75
        LIMIT 10
    """

    cur.execute(query)
    controls = cur.fetchall()

    print(f"\n✓ Testing transform on {len(controls)} controls")

    transformed = []
    for control in controls:
        constraint = simulate_transform(control)
        transformed.append(constraint)

        # Validate transformed constraint
        assert 'type' in constraint, "Missing 'type' field"
        assert 'value' in constraint, "Missing 'value' field"
        assert 'source' in constraint, "Missing 'source' field"
        assert 'provision_id' in constraint, "Missing 'provision_id' field"

        assert constraint['type'] in ['height', 'fsr', 'setback', 'special', 'environmental'], \
            f"Invalid type: {constraint['type']}"

        assert constraint['source']['authority_level'] in ['LEP', 'DCP', 'SEPP'], \
            f"Invalid authority: {constraint['source']['authority_level']}"

    print(f"\n✓ Sample transformed constraints:")
    for i, c in enumerate(transformed[:5]):
        print(f"\n  [{i+1}] Type: {c['type']}")
        print(f"      Value: {c['value']} {c['unit'] or ''}")
        print(f"      Source: {c['source']['document'][:40]}...")
        print(f"      Authority: {c['source']['authority_level']}")
        print(f"      Confidence: {c['confidence']}")
        print(f"      Provision ID: {c['provision_id']}")

    # Check type distribution
    by_type = {}
    for c in transformed:
        by_type[c['type']] = by_type.get(c['type'], 0) + 1

    print(f"\n✓ Transformed constraint types:")
    for ctype, count in sorted(by_type.items()):
        print(f"  - {ctype}: {count}")

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 1 PASSED: Controls transform correctly")
    print("="*80)
    return True


def test_transform_setback_rules():
    """Test transforming zone_setback_rules results"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 2: TRANSFORM SETBACK RULES")
    print("="*80)

    # Get setback rules
    query = """
        SELECT
            'setback' as control_type,
            boundary_type as control_subtype,
            base_value as value_numeric,
            unit,
            confidence,
            NULL as provision_id,
            'Curated setback rule from ' || source_document as provision_text,
            source_clause as ref_number,
            source_document as section_header,
            source_document as document_id,
            zone
        FROM zone_setback_rules
        WHERE zone = 'R2'
          AND confidence::numeric > 0.90
    """

    cur.execute(query)
    rules = cur.fetchall()

    print(f"\n✓ Testing transform on {len(rules)} setback rules")

    transformed = []
    for rule in rules:
        constraint = simulate_transform(rule)
        transformed.append(constraint)

        # Validate
        assert constraint['type'] == 'setback', f"Expected type 'setback', got {constraint['type']}"
        assert constraint['subtype'] in ['front', 'side', 'rear'], \
            f"Invalid subtype: {constraint['subtype']}"
        assert isinstance(constraint['value'], float), \
            f"Value should be float, got {type(constraint['value'])}"
        assert constraint['confidence'] > 0.90, \
            f"Confidence should be >0.90, got {constraint['confidence']}"

    print(f"\n✓ Transformed setback constraints:")
    for c in sorted(transformed, key=lambda x: ['front', 'side', 'rear'].index(x['subtype'])):
        print(f"  - {c['subtype']}: {c['value']} {c['unit']} (confidence: {c['confidence']})")
        print(f"    Source: {c['source']['document'][:50]}...")

    # Check we have all boundary types
    subtypes = {c['subtype'] for c in transformed}
    print(f"\n✓ Boundary types present: {', '.join(sorted(subtypes))}")
    assert 'front' in subtypes, "Missing front setback"
    assert 'side' in subtypes, "Missing side setback"
    assert 'rear' in subtypes, "Missing rear setback"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 2 PASSED: Setback rules transform correctly")
    print("="*80)
    return True


def test_api_response_structure():
    """Test that transformed data matches expected API response structure"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("TEST 3: API RESPONSE STRUCTURE")
    print("="*80)

    # Get controls
    cur.execute("""
        SELECT
            dc.control_type, dc.control_subtype, dc.value_numeric, dc.unit, dc.confidence_score,
            rp.id, rp.provision_text, rp.ref_number, rp.section_header, rp.document_id, rp.zone
        FROM development_controls dc
        JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
        WHERE rp.zone = 'R2'
          AND dc.control_type IN ('height', 'setback', 'parking', 'fsr')
          AND dc.value_numeric IS NOT NULL
          AND dc.confidence_score::numeric > 0.75
        LIMIT 15
    """)
    controls = cur.fetchall()

    # Get setback rules
    cur.execute("""
        SELECT
            'setback', boundary_type, base_value, unit, confidence,
            NULL, 'Curated rule', source_clause, source_document, source_document, zone
        FROM zone_setback_rules
        WHERE zone = 'R2' AND confidence::numeric > 0.90
    """)
    setbacks = cur.fetchall()

    # Transform all
    all_constraints = [simulate_transform(c) for c in controls + setbacks]

    # Categorize as API would
    api_response = {
        'building_envelope': [c for c in all_constraints if c['type'] in ['height', 'fsr', 'setback']],
        'environmental': [c for c in all_constraints if c['type'] == 'environmental'],
        'special_provisions': [c for c in all_constraints if c['type'] == 'special']
    }

    print(f"\n✓ API response structure:")
    print(f"  - building_envelope: {len(api_response['building_envelope'])} items")
    print(f"  - environmental: {len(api_response['environmental'])} items")
    print(f"  - special_provisions: {len(api_response['special_provisions'])} items")

    # Validate building envelope
    envelope = api_response['building_envelope']
    assert len(envelope) >= 5, f"Expected at least 5 building envelope items, got {len(envelope)}"

    print(f"\n✓ Building envelope breakdown:")
    by_type = {}
    for c in envelope:
        by_type[c['type']] = by_type.get(c['type'], 0) + 1
    for ctype, count in sorted(by_type.items()):
        print(f"  - {ctype}: {count}")

    # Check setbacks specifically
    setback_items = [c for c in envelope if c['type'] == 'setback']
    setback_subtypes = {c['subtype'] for c in setback_items if c.get('subtype')}

    print(f"\n✓ Setback constraints: {len(setback_items)}")
    print(f"  Subtypes: {', '.join(sorted(setback_subtypes))}")

    assert 'front' in setback_subtypes, "Missing front setback in response"
    assert 'side' in setback_subtypes, "Missing side setback in response"
    assert 'rear' in setback_subtypes, "Missing rear setback in response"

    # Sample items
    print(f"\n✓ Sample building envelope items:")
    for i, c in enumerate(envelope[:6]):
        subtype_str = f" ({c['subtype']})" if c.get('subtype') else ""
        print(f"  [{i+1}] {c['type']}{subtype_str}: {c['value']} {c['unit'] or ''}")

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ TEST 3 PASSED: API response structure is correct")
    print("="*80)
    return True


if __name__ == '__main__':
    try:
        test_transform_controls()
        test_transform_setback_rules()
        test_api_response_structure()

        print("\n" + "="*80)
        print("✓ ALL TRANSFORM TESTS PASSED")
        print("="*80)
        print("\nData transforms correctly into expected API response format")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)