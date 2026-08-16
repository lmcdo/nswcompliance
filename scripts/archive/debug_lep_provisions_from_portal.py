#!/usr/bin/env python3
"""
Debug what the Planning Portal returns for Key Sites addresses.
Check if localProvisions are in the Portal response.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import requests
import json

# Test addresses for Key Sites
TEST_ADDRESSES = [
    '45 Lilyfield Road, Rozelle NSW 2039',  # Clause 6.21
    '126 Parramatta Road, Stanmore NSW 2048',  # Clause 6.33
    '10 Perry Street, Lilyfield NSW 2040',  # Clause 6.31
]

def test_property_api_raw(address: str):
    """Test property API and show raw response."""

    print('=' * 80)
    print(f'ADDRESS: {address}')
    print('=' * 80)
    print()

    url = 'http://localhost:3003/api/property'
    params = {'address': address}

    try:
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            data = response.json()

            # Show what we got
            print('✅ API Response Status: 200 OK')
            print()

            # Check constraints
            constraints = data.get('constraints', {})
            print('CONSTRAINTS:')
            print(f'  LGA: {constraints.get("lga")}')
            print(f'  Zone: {constraints.get("zone")}')
            print(f'  Heritage: {constraints.get("heritage")}')
            print()

            # Check localProvisions
            local_provisions = constraints.get('localProvisions', [])
            print(f'LOCAL PROVISIONS: {len(local_provisions)} found')

            if len(local_provisions) > 0:
                print()
                for i, prov in enumerate(local_provisions, 1):
                    print(f'  {i}. {prov.get("title", "No title")}')
                    print(f'     Clause: {prov.get("clauseNumber", "N/A")}')
                    print(f'     Map Type: {prov.get("mapType", "N/A")}')
                    print(f'     Class: {prov.get("class", "N/A")}')
                    print()
            else:
                print('  ⚠️  No local provisions returned')
                print()

                # Check if Planning Portal returned ANY layers
                planning_layers = data.get('planningLayers', [])
                print(f'PLANNING LAYERS: {len(planning_layers)} found')

                if len(planning_layers) > 0:
                    # Look for Key Sites Map layer
                    ksm_layer = None
                    for layer in planning_layers:
                        layer_name = layer.get('layerName', '')
                        if 'Key Sites' in layer_name or 'Site' in layer_name:
                            ksm_layer = layer
                            break

                    if ksm_layer:
                        print()
                        print(f'FOUND KEY SITES LAYER: {ksm_layer.get("layerName")}')
                        print(f'  Results: {len(ksm_layer.get("results", []))}')

                        if ksm_layer.get('results'):
                            for result in ksm_layer['results']:
                                print(f'  - {result.get("Legislative Clause", "N/A")}')
                    else:
                        print()
                        print('Available layers:')
                        for layer in planning_layers[:10]:
                            print(f'  - {layer.get("layerName")}')

        else:
            print(f'❌ API failed: HTTP {response.status_code}')
            print(response.text[:500])

    except Exception as e:
        print(f'❌ Error: {e}')

    print()


def main():
    """Test all addresses."""

    print('=' * 80)
    print('DEBUG: LEP PROVISIONS FROM PLANNING PORTAL')
    print('=' * 80)
    print()
    print('Testing if Planning Portal returns Key Sites Map data')
    print('for addresses that should have LEP Part 6 provisions')
    print()

    for address in TEST_ADDRESSES:
        test_property_api_raw(address)

    print('=' * 80)
    print('ANALYSIS')
    print('=' * 80)
    print()
    print('If localProvisions are empty:')
    print('  1. Address may not be within Key Sites Map boundary')
    print('  2. Planning Portal may not have data for this address')
    print('  3. Property API mapping logic may not handle this provision type')
    print()
    print('Check Planning Portal directly:')
    print('  https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address')


if __name__ == '__main__':
    main()
