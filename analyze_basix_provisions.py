#!/usr/bin/env python3
"""
Analyze BASIX and other provisions returned by NSW Planning API
"""

import asyncio
import json
import sys
sys.path.append('services')

from nsw_planning_api import NSWPlanningAPI

async def analyze_api_provisions():
    """Analyze what provisions the NSW Planning API returns"""

    print("=== NSW PLANNING API PROVISIONS ANALYSIS ===")
    print()

    # Test with a known Inner West property
    test_address = "45 Liverpool Street, Ashfield NSW 2131"

    async with NSWPlanningAPI() as api:
        print(f"Testing with: {test_address}")

        # Get property ID
        property_results = await api.lookup_property_id(test_address)
        if not property_results:
            print("Property not found")
            return

        prop_id = property_results[0]['propId']
        print(f"Property ID: {prop_id}")
        print()

        # Get all planning controls
        print("1. ALL PLANNING CONTROLS RETURNED:")
        print("-" * 50)

        controls = await api.get_planning_controls(prop_id)
        print(f"Total control layers: {len(controls)}")

        for i, control in enumerate(controls, 1):
            layer_name = control.get('layerName', 'Unknown')
            results = control.get('results', [])

            print(f"\n{i}. {layer_name}")
            print(f"   Results: {len(results)}")

            # Look for BASIX specifically
            if 'basix' in layer_name.lower() or any('basix' in str(r).lower() for r in results):
                print("   *** BASIX PROVISIONS FOUND ***")

            # Show sample result data
            if results:
                sample = results[0]
                print(f"   Sample fields: {list(sample.keys())}")

                # Look for specific provision types
                for key, value in sample.items():
                    if 'basix' in str(value).lower():
                        print(f"   BASIX: {key} = {value}")
                    elif 'climate' in str(value).lower():
                        print(f"   Climate: {key} = {value}")
                    elif 'water' in str(value).lower():
                        print(f"   Water: {key} = {value}")
                    elif 'energy' in str(value).lower():
                        print(f"   Energy: {key} = {value}")

        print("\n" + "="*50)
        print("2. SPECIAL PROVISIONS ANALYSIS")
        print("="*50)

        # Look specifically for Special Provisions layer (which contains BASIX)
        special_provisions = None
        for control in controls:
            if 'Special Provisions' in control.get('layerName', ''):
                special_provisions = control
                break

        if special_provisions:
            print("SPECIAL PROVISIONS LAYER FOUND:")
            results = special_provisions.get('results', [])
            print(f"Total special provisions: {len(results)}")

            basix_provisions = []
            other_provisions = []

            for result in results:
                result_str = str(result).lower()
                if 'basix' in result_str:
                    basix_provisions.append(result)
                else:
                    other_provisions.append(result)

            print(f"\nBASIX Provisions: {len(basix_provisions)}")
            for i, basix in enumerate(basix_provisions, 1):
                print(f"  BASIX {i}:")
                for key, value in basix.items():
                    print(f"    {key}: {value}")

            print(f"\nOther Special Provisions: {len(other_provisions)}")
            for i, other in enumerate(other_provisions[:3], 1):  # Show first 3
                print(f"  Other {i}:")
                for key, value in other.items():
                    print(f"    {key}: {value}")

        else:
            print("No Special Provisions layer found")

        print("\n" + "="*50)
        print("3. CURRENT HANDLING ANALYSIS")
        print("="*50)

        # Check how these are currently handled in PropertyIntelligence
        intelligence = await api.get_property_intelligence(test_address)

        print("Current PropertyIntelligence handling:")
        print(f"  Main zone: {intelligence.zone.value if intelligence.zone else 'None'}")
        print(f"  Height limit: {intelligence.height_limit.value if intelligence.height_limit else 'None'}")
        print(f"  FSR limit: {intelligence.fsr_limit.value if intelligence.fsr_limit else 'None'}")
        print(f"  Heritage items: {len(intelligence.heritage_items)}")
        print(f"  Other controls: {len(intelligence.other_controls)}")

        # Check if BASIX is in other_controls
        basix_in_other = []
        for control in intelligence.other_controls:
            if 'basix' in control.layer_name.lower():
                basix_in_other.append(control)

        print(f"  BASIX in other_controls: {len(basix_in_other)}")
        for basix in basix_in_other:
            print(f"    {basix.layer_name}: {basix.value}")

        print("\n" + "="*50)
        print("4. RECOMMENDATIONS")
        print("="*50)

        print("Current gaps and recommendations:")
        print("1. BASIX provisions are captured but not prominently exposed")
        print("2. Special provisions include multiple SEPP overlays that should be parsed")
        print("3. Climate zones, water use standards not specifically handled")
        print("4. Energy efficiency requirements not extracted")
        print("5. Need dedicated BASIX compliance checking")

        # Save raw data for analysis
        api_data = {
            'property_id': prop_id,
            'all_controls': controls,
            'property_intelligence': {
                'zone': intelligence.zone.value if intelligence.zone else None,
                'height_limit': intelligence.height_limit.value if intelligence.height_limit else None,
                'fsr_limit': intelligence.fsr_limit.value if intelligence.fsr_limit else None,
                'heritage_items_count': len(intelligence.heritage_items),
                'other_controls_count': len(intelligence.other_controls),
                'other_controls': [
                    {
                        'layer_name': c.layer_name,
                        'value': c.value,
                        'units': c.units
                    } for c in intelligence.other_controls
                ]
            }
        }

        with open('nsw_api_provisions_analysis.json', 'w') as f:
            json.dump(api_data, f, indent=2, default=str)

        print("\nDetailed analysis saved to: nsw_api_provisions_analysis.json")

if __name__ == "__main__":
    asyncio.run(analyze_api_provisions())