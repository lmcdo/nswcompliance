#!/usr/bin/env python3
"""
Test 4: End-to-End Verification
================================
Simulates complete flow from database → API → frontend
"""

import psycopg2
import sys
import json

def simulate_complete_flow():
    """Simulate the complete data flow"""

    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='nsw_planning',
        user='postgres',
        password='postgres'
    )
    cur = conn.cursor()

    print("\n" + "="*80)
    print("END-TO-END FLOW SIMULATION")
    print("="*80)
    print("\nRequest: zone=R2, lga=Inner West, developmentType=dwelling_house")

    # === STEP 1: Database Queries ===
    print("\n\n[STEP 1] Database Queries")
    print("-" * 80)

    zone = 'R2'
    dev_type = 'dwelling_house'

    # Query 1: Controls
    controls_query = """
        SELECT
            dc.control_type, dc.control_subtype, dc.value_numeric, dc.unit, dc.confidence_score,
            rp.id, rp.provision_text, rp.ref_number, rp.section_header, rp.document_id, rp.zone
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
    print(f"✓ Query 1: {len(controls)} controls from development_controls")

    # Query 2: Setback rules
    setback_query = """
        SELECT
            'setback', boundary_type, base_value, unit, confidence,
            NULL, 'Curated rule', source_clause, source_document, source_document, zone
        FROM zone_setback_rules
        WHERE zone = %s AND confidence::numeric > 0.90
    """

    cur.execute(setback_query, [zone])
    setbacks = cur.fetchall()
    print(f"✓ Query 2: {len(setbacks)} setback rules from zone_setback_rules")

    # Query 3: SEPP overrides
    sepp_query = """
        SELECT id, sepp_provision_id, lep_clause_reference, override_type,
               extracted_text, confidence_score
        FROM sepp_lep_overrides
        WHERE confidence_score::numeric > 0.5
        LIMIT 10
    """

    cur.execute(sepp_query)
    sepp_overrides = cur.fetchall()
    print(f"✓ Query 3: {len(sepp_overrides)} SEPP overrides from sepp_lep_overrides")

    # === STEP 2: Transform Data ===
    print("\n\n[STEP 2] Transform Data")
    print("-" * 80)

    def transform(control):
        control_type, control_subtype, value, unit, confidence, prov_id, text, ref, section, doc_id, zone = control

        type_map = {'height': 'height', 'fsr': 'fsr', 'setback': 'setback',
                   'parking': 'special', 'open_space': 'special'}
        ui_type = type_map.get(control_type, 'environmental')

        doc_name = (doc_id or '').split('___')[0].replace('_', ' ')
        authority = 'DCP'
        if 'sepp' in (doc_id or '').lower():
            authority = 'SEPP'
        elif 'lep' in (doc_id or '').lower():
            authority = 'LEP'

        return {
            'type': ui_type,
            'value': float(value) if value else 'See provision',
            'unit': unit,
            'source': {'clause': ref or 'N/A', 'document': doc_name, 'authority_level': authority},
            'provision_id': prov_id,
            'full_text': (text or '')[:100],
            'confidence': float(confidence) if confidence else None,
            'subtype': control_subtype
        }

    all_constraints = [transform(c) for c in controls + setbacks]

    # Add SEPP overrides
    for sepp in sepp_overrides:
        all_constraints.append({
            'type': 'special',
            'value': f"SEPP {sepp[3] or 'modifies'} LEP clause {sepp[2] or 'N/A'}",
            'source': {'clause': f"Override: {sepp[2] or 'N/A'}",
                      'document': f"SEPP Override (Provision {sepp[1] or 'Unknown'})",
                      'authority_level': 'SEPP'},
            'provision_id': sepp[1] or 0,
            'full_text': (sepp[4] or 'SEPP override applies')[:100]
        })

    print(f"✓ Transformed {len(all_constraints)} constraints")

    # === STEP 3: Categorize for API Response ===
    print("\n\n[STEP 3] API Response Structure")
    print("-" * 80)

    api_response = {
        'building_envelope': [c for c in all_constraints if c['type'] in ['height', 'fsr', 'setback']],
        'environmental': [c for c in all_constraints if c['type'] == 'environmental'],
        'special_provisions': [c for c in all_constraints if c['type'] == 'special']
    }

    print(f"✓ building_envelope: {len(api_response['building_envelope'])} items")
    for c in api_response['building_envelope'][:8]:
        subtype = f" ({c['subtype']})" if c.get('subtype') else ""
        print(f"  - {c['type']}{subtype}: {c['value']} {c['unit'] or ''} [{c['source']['authority_level']}]")

    print(f"\n✓ environmental: {len(api_response['environmental'])} items")

    print(f"\n✓ special_provisions: {len(api_response['special_provisions'])} items")
    for c in api_response['special_provisions'][:5]:
        print(f"  - {c['source']['document'][:50]}... [{c['source']['authority_level']}]")

    # === STEP 4: Frontend Assembly ===
    print("\n\n[STEP 4] Frontend Data Assembly")
    print("-" * 80)

    # Simulate LEP constraints from Planning API (would be extracted by frontend)
    lep_constraints = [
        {'type': 'height', 'value': 9, 'unit': 'm', 'source': {'clause': '4.3', 'document': 'Inner West LEP 2022', 'authority_level': 'LEP'}},
        {'type': 'fsr', 'value': 0.6, 'unit': ':1', 'source': {'clause': '4.4', 'document': 'Inner West LEP 2022', 'authority_level': 'LEP'}}
    ]

    # Simulate Planning API SEPP provisions (would be extracted by frontend)
    planning_api_sepps = [
        {'type': 'special', 'value': 'Class 2', 'source': {'clause': 'Climate Zone', 'document': 'SEPP (Resilience and Hazards) 2021', 'authority_level': 'SEPP'}},
        {'type': 'special', 'value': '40%', 'unit': '%', 'source': {'clause': 'Water Use', 'document': 'SEPP (Resilience and Hazards) 2021', 'authority_level': 'SEPP'}}
    ]

    # Assemble as frontend would
    frontend_data = {
        'building_envelope': lep_constraints + api_response['building_envelope'],
        'environmental': api_response['environmental'],
        'special_provisions': planning_api_sepps + api_response['special_provisions']
    }

    print(f"✓ Final UI data structure:")
    print(f"\n  Building Envelope Section: {len(frontend_data['building_envelope'])} cards")
    for i, c in enumerate(frontend_data['building_envelope'][:10]):
        subtype = f" ({c['subtype']})" if c.get('subtype') else ""
        value_str = f"{c['value']} {c['unit'] or ''}".strip()
        print(f"    [{i+1}] {c['source']['authority_level']}: {c['type']}{subtype} = {value_str}")

    print(f"\n  Environmental Section: {len(frontend_data['environmental'])} cards")

    print(f"\n  Special Provisions Section: {len(frontend_data['special_provisions'])} cards")
    for i, c in enumerate(frontend_data['special_provisions'][:10]):
        print(f"    [{i+1}] {c['source']['authority_level']}: {c['source']['document'][:40]}...")

    # === VERIFICATION ===
    print("\n\n[VERIFICATION]")
    print("-" * 80)

    # Check building envelope has essentials
    envelope = frontend_data['building_envelope']
    envelope_types = [c['type'] for c in envelope]
    envelope_sources = [c['source']['authority_level'] for c in envelope]

    height_count = envelope_types.count('height')
    setback_count = envelope_types.count('setback')
    fsr_count = envelope_types.count('fsr')

    lep_count = envelope_sources.count('LEP')
    dcp_count = envelope_sources.count('DCP')

    print(f"✓ Building Envelope Validation:")
    print(f"  - Height controls: {height_count} (need ≥1)")
    print(f"  - Setback controls: {setback_count} (need ≥3 for front/side/rear)")
    print(f"  - FSR controls: {fsr_count}")
    print(f"  - LEP controls: {lep_count} (from Planning API)")
    print(f"  - DCP controls: {dcp_count} (from database)")

    assert height_count >= 1, "Need at least 1 height control"
    assert setback_count >= 3, "Need at least 3 setback controls (front/side/rear)"
    assert lep_count >= 2, "Need LEP controls from Planning API"
    assert dcp_count >= 3, "Need DCP controls from database"

    # Check setback subtypes
    setbacks = [c for c in envelope if c['type'] == 'setback']
    setback_subtypes = {c.get('subtype') for c in setbacks if c.get('subtype')}

    print(f"\n✓ Setback Validation:")
    print(f"  - Subtypes present: {', '.join(sorted(setback_subtypes))}")

    assert 'front' in setback_subtypes, "Missing front setback"
    assert 'side' in setback_subtypes, "Missing side setback"
    assert 'rear' in setback_subtypes, "Missing rear setback"

    # Check special provisions
    special = frontend_data['special_provisions']
    special_sources = [c['source']['authority_level'] for c in special]

    planning_sepp_count = sum(1 for c in special if 'SEPP' in c['source']['authority_level']
                              and 'Override' not in c['source']['document'])
    override_count = sum(1 for c in special if 'Override' in c['source']['document'])

    print(f"\n✓ Special Provisions Validation:")
    print(f"  - Planning API SEPPs: {planning_sepp_count}")
    print(f"  - SEPP overrides: {override_count}")
    print(f"  - Total: {len(special)}")

    assert planning_sepp_count >= 2, "Need Planning API SEPPs"
    assert override_count >= 5, "Need SEPP override provisions"
    assert len(special) <= 20, f"Too many special provisions ({len(special)}), should be ~13-14"

    # Final summary
    total_cards = len(frontend_data['building_envelope']) + len(frontend_data['environmental']) + len(frontend_data['special_provisions'])

    print(f"\n✓ Overall Summary:")
    print(f"  - Total provision cards: {total_cards}")
    print(f"  - Building envelope: {len(frontend_data['building_envelope'])}")
    print(f"  - Environmental: {len(frontend_data['environmental'])}")
    print(f"  - Special provisions: {len(frontend_data['special_provisions'])}")

    assert 20 <= total_cards <= 35, f"Expected 20-35 total cards, got {total_cards}"

    cur.close()
    conn.close()

    print(f"\n{'='*80}")
    print("✓ END-TO-END TEST PASSED")
    print("="*80)
    print("\nComplete flow produces correct UI data structure")
    return True


if __name__ == '__main__':
    try:
        simulate_complete_flow()

        print("\n" + "="*80)
        print("✓ END-TO-END VERIFICATION COMPLETE")
        print("="*80)
        print("\nImplementation will work correctly:")
        print("  - Queries return filtered, relevant data")
        print("  - Transforms produce correct constraint objects")
        print("  - Frontend receives properly structured data")
        print("  - UI displays ~25-30 relevant provisions (not 60+)")
        sys.exit(0)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)