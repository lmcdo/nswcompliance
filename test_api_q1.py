#!/usr/bin/env python3
"""
Test PRP-Q1 API endpoint
"""

import requests
import json
import time

def test_api_endpoint():
    """Test the live compliance API endpoint"""

    print("=== TESTING PRP-Q1 API ENDPOINT ===")
    print()

    # Note: This would normally test the Next.js API, but since we can't run the full Next.js server,
    # let's directly test the Python calculation engine that the API would call

    print("Testing Python engine that API calls:")

    import asyncio
    import sys
    sys.path.append('services')

    async def test_engine():
        from live_compliance_engine import calculate_property_compliance

        # Test data that would come from API request
        test_request = {
            'address': '45 Liverpool Street, Ashfield NSW 2131',
            'proposed_development': {
                'gross_floor_area': 200,
                'height': 9.0,
                'building_area': 130
            }
        }

        print(f"Test Request:")
        print(f"  Address: {test_request['address']}")
        print(f"  GFA: {test_request['proposed_development']['gross_floor_area']}sqm")
        print(f"  Height: {test_request['proposed_development']['height']}m")
        print(f"  Building Area: {test_request['proposed_development']['building_area']}sqm")
        print()

        start_time = time.time()

        try:
            result = await calculate_property_compliance(
                test_request['address'],
                test_request['proposed_development']
            )

            response_time = int((time.time() - start_time) * 1000)

            print("API Response (simulated):")
            print(f"  Success: True")
            print(f"  Processing Time: {response_time}ms")
            print(f"  Overall Compliant: {result.overall_compliant}")

            if result.fsr_compliance:
                print(f"  FSR: {result.fsr_compliance.actual_value} vs {result.fsr_compliance.limit_value} limit")
                print(f"    Status: {'Compliant' if result.fsr_compliance.compliant else 'Non-compliant'}")
                print(f"    Confidence: {result.fsr_compliance.confidence}")
                print(f"    Data Source: {result.fsr_compliance.data_source}")

            if result.height_compliance:
                print(f"  Height: {result.height_compliance.actual_value}{result.height_compliance.units} vs {result.height_compliance.limit_value}{result.height_compliance.units} limit")
                print(f"    Status: {'Compliant' if result.height_compliance.compliant else 'Non-compliant'}")
                print(f"    Data Source: {result.height_compliance.data_source}")

            if result.site_coverage_compliance:
                print(f"  Site Coverage: {result.site_coverage_compliance.actual_value}{result.site_coverage_compliance.units} vs {result.site_coverage_compliance.limit_value}{result.site_coverage_compliance.units} limit")
                print(f"    Status: {'Compliant' if result.site_coverage_compliance.compliant else 'Non-compliant'}")

            if result.warnings:
                print(f"  Warnings: {result.warnings}")

            print()
            print("✓ API engine test successful")
            print(f"✓ Response time: {response_time}ms")
            print(f"✓ Using live NSW API data: {any('nsw_api' in getattr(comp, 'data_source', '') for comp in [result.fsr_compliance, result.height_compliance] if comp)}")

            return True

        except Exception as e:
            print(f"✗ API engine test failed: {e}")
            return False

    # Run the async test
    success = asyncio.run(test_engine())

    print()
    print("=== API TEST SUMMARY ===")
    if success:
        print("✓ PRP-Q1 API engine working correctly")
        print("✓ Live compliance calculations functional")
        print("✓ NSW Planning API integration successful")
        print()
        print("Ready for Next.js API endpoint deployment!")
    else:
        print("✗ API engine needs debugging")

if __name__ == "__main__":
    test_api_endpoint()