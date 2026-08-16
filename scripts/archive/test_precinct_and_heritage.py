"""
Comprehensive test of precinct and heritage filtering.
Tests all 3 councils + heritage HCA code resolution.
"""

import requests
import json
from typing import Dict, List

BASE_URL = "http://localhost:3003/api/provisions/for-property"

def test_api_call(test_name: str, params: Dict) -> Dict:
    """Make API call and return results."""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)
    print(f"Parameters: {json.dumps(params, indent=2)}")

    try:
        response = requests.get(BASE_URL, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()

        print(f"\nStatus: {response.status_code}")
        print(f"Total provisions: {len(data.get('provisions', []))}")

        # Count by layer
        layers = {}
        for prov in data.get('provisions', []):
            layer = prov.get('v2_dcp_layer', 'unknown')
            layers[layer] = layers.get(layer, 0) + 1

        print(f"\nBy layer:")
        for layer, count in sorted(layers.items()):
            print(f"  {layer}: {count} provisions")

        # Check precinct provisions specifically
        if 'precinct' in layers:
            precinct_provs = [p for p in data.get('provisions', []) if p.get('v2_dcp_layer') == 'precinct']
            precinct_ids = set(p.get('v2_precinct_id') for p in precinct_provs if p.get('v2_precinct_id'))
            print(f"\nPrecinct IDs found: {precinct_ids}")

            # Show first 3 precinct provisions
            print(f"\nSample precinct provisions:")
            for prov in precinct_provs[:3]:
                text_preview = prov.get('provision_text', '')[:80]
                print(f"  - ID {prov.get('id')}: {text_preview}...")

        # Check heritage provisions
        heritage_provs = [p for p in data.get('provisions', []) if p.get('v2_topic') == 'heritage']
        if heritage_provs:
            print(f"\nHeritage provisions: {len(heritage_provs)}")
            hcas = set(p.get('v2_heritage_hca') for p in heritage_provs if p.get('v2_heritage_hca'))
            print(f"HCAs found: {hcas}")

        return {
            'success': True,
            'total': len(data.get('provisions', [])),
            'by_layer': layers,
            'data': data
        }

    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to API. Is the dev server running?")
        print("Start with: cd frontend-nextjs && npm run dev")
        return {'success': False, 'error': 'Connection refused'}
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return {'success': False, 'error': str(e)}

def main():
    """Run all tests."""
    print("=" * 80)
    print("PRECINCT AND HERITAGE FILTERING TESTS")
    print("=" * 80)
    print("\nThis script will test:")
    print("  1. Marrickville precinct filtering (Precinct 47_)")
    print("  2. Leichhardt Distinctive Neighbourhood (C2.2.1.1)")
    print("  3. Leichhardt Part G site (with PART_G_OVERVIEW)")
    print("  4. Ashfield precinct (Part 6 - Parramatta Road)")
    print("  5. Heritage HCA code resolution (C35)")
    print("\nMake sure Next.js dev server is running on port 3003")
    print("Press Enter to continue...")
    input()

    results = []

    # Test 1: Marrickville Precinct 47_ (Victoria Road)
    results.append(test_api_call(
        "Marrickville Precinct 47_ (Victoria Road)",
        {
            'lga': 'Inner West',
            'former_council': 'Marrickville',
            'precinct_id': '47_',
        }
    ))

    # Test 2: Leichhardt Distinctive Neighbourhood C2.2.1.1 (Young Street)
    results.append(test_api_call(
        "Leichhardt Distinctive Neighbourhood C2.2.1.1 (Young Street)",
        {
            'lga': 'Inner West',
            'former_council': 'Leichhardt',
            'precinct_id': 'C2.2.1.1',
        }
    ))

    # Test 3: Leichhardt Part G site (should include PART_G_OVERVIEW)
    # Using C2.2.1.3 (Johnston Street) which has Part G provisions
    results.append(test_api_call(
        "Leichhardt with PART_G_OVERVIEW (any precinct should include it)",
        {
            'lga': 'Inner West',
            'former_council': 'Leichhardt',
            'precinct_id': 'C2.2.1.3',
        }
    ))

    # Test 4: Ashfield Part 6 (Parramatta Road Enterprise)
    results.append(test_api_call(
        "Ashfield Part 6 (Parramatta Road Enterprise Zone)",
        {
            'lga': 'Inner West',
            'former_council': 'Ashfield',
            'precinct_id': 'Part 6',
        }
    ))

    # Test 5: Heritage with HCA code (C35 = Parramatta Road HCA)
    results.append(test_api_call(
        "Heritage with HCA C35 (Parramatta Road HCA)",
        {
            'lga': 'Inner West',
            'former_council': 'Leichhardt',
            'heritage': 'true',
            'hca': 'C35',
        }
    ))

    # Test 6: Marrickville heritage with HCA
    results.append(test_api_call(
        "Marrickville Heritage with HCA 10",
        {
            'lga': 'Inner West',
            'former_council': 'Marrickville',
            'heritage': 'true',
            'hca': 'HCA 10',
        }
    ))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    success_count = sum(1 for r in results if r.get('success'))
    print(f"\nTests passed: {success_count}/{len(results)}")

    print("\nResults by test:")
    test_names = [
        "Marrickville Precinct 47_",
        "Leichhardt DN C2.2.1.1",
        "Leichhardt PART_G_OVERVIEW",
        "Ashfield Part 6",
        "Heritage HCA C35",
        "Marrickville HCA 10",
    ]

    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "[OK]" if result.get('success') else "[FAIL]"
        total = result.get('total', 0)
        print(f"\n{status} {name}")
        if result.get('success'):
            print(f"    Total provisions: {total}")
            layers = result.get('by_layer', {})
            if 'precinct' in layers:
                print(f"    Precinct provisions: {layers['precinct']}")
        else:
            print(f"    Error: {result.get('error')}")

    # Expected results validation
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    print("\nExpected results:")
    print("  1. Marrickville 47_: Should have ~54 precinct provisions")
    print("  2. Leichhardt C2.2.1.1: Should have ~7 precinct provisions")
    print("  3. Leichhardt PART_G_OVERVIEW: Should have ~415+ precinct provisions (overview)")
    print("  4. Ashfield Part 6: Should have ~45 precinct provisions")
    print("  5. Heritage C35: Should have heritage provisions with v2_heritage_hca='C35'")
    print("  6. Marrickville HCA 10: Should have heritage provisions with v2_heritage_hca='hca_10'")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
