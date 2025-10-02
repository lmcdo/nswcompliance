"""
Phase 2: API Integration Tests
Objective: Verify all Phase 2 API endpoints work correctly
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:3000"

def test_cross_references_api():
    """Test cross-reference resolution endpoint"""
    print("\n" + "=" * 80)
    print("TEST 1: CROSS-REFERENCE API")
    print("=" * 80)

    # Get a provision that has cross-references
    test_provision_id = 1  # Adjust based on actual data

    url = f"{BASE_URL}/api/provisions/cross-references?provision_id={test_provision_id}"

    try:
        response = requests.get(url, timeout=5)
        print(f"\nEndpoint: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Response time: {data.get('meta', {}).get('responseTimeMs')}ms")
            print(f"Total cross-references: {data.get('data', {}).get('totalCount')}")
            print(f"Resolved count: {data.get('data', {}).get('resolvedCount')}")

            # Show first reference
            refs = data.get('data', {}).get('crossReferences', [])
            if refs:
                first_ref = refs[0]
                print(f"\nFirst reference:")
                print(f"  Type: {first_ref.get('referenceType')}")
                print(f"  Number: {first_ref.get('referenceNumber')}")
                print(f"  Status: {first_ref.get('resolutionStatus')}")
                print(f"  Mandatory: {first_ref.get('isMandatory')}")

            return response.status_code == 200
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_zone_applicability_api():
    """Test zone applicability query endpoint"""
    print("\n" + "=" * 80)
    print("TEST 2: ZONE APPLICABILITY API")
    print("=" * 80)

    test_zone = "R2"
    url = f"{BASE_URL}/api/provisions/zone-applicability?zone={test_zone}&limit=10"

    try:
        response = requests.get(url, timeout=5)
        print(f"\nEndpoint: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Response time: {data.get('meta', {}).get('responseTimeMs')}ms")
            print(f"Total provisions: {data.get('data', {}).get('totalCount')}")

            # Show provisions by priority
            by_priority = data.get('data', {}).get('byPriority', {})
            print(f"\nProvisions by priority:")
            for priority in sorted(by_priority.keys()):
                count = len(by_priority[priority])
                print(f"  Priority {priority}: {count} provisions")

            # Show first provision
            provisions = data.get('data', {}).get('provisions', [])
            if provisions:
                first = provisions[0]
                print(f"\nFirst provision:")
                print(f"  Ref: {first.get('refNumber')}")
                print(f"  Category: {first.get('provisionCategory')}")
                print(f"  Applicability source: {first.get('applicabilitySource')}")
                print(f"  Confidence: {first.get('confidenceScore')}")

            return response.status_code == 200
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_control_codes_api():
    """Test control code search endpoint"""
    print("\n" + "=" * 80)
    print("TEST 3: CONTROL CODE SEARCH API")
    print("=" * 80)

    test_code = "C17"
    url = f"{BASE_URL}/api/provisions/control-codes?code={test_code}"

    try:
        response = requests.get(url, timeout=5)
        print(f"\nEndpoint: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Response time: {data.get('meta', {}).get('responseTimeMs')}ms")
            print(f"Total provisions: {data.get('data', {}).get('totalCount')}")

            # Show control types
            by_type = data.get('data', {}).get('byControlType', {})
            print(f"\nControl types found:")
            for ctrl_type, provisions in by_type.items():
                print(f"  {ctrl_type}: {len(provisions)} provisions")

            # Show code groups
            by_group = data.get('data', {}).get('byCodeGroup', {})
            print(f"\nCode groups (consolidated display):")
            for group, provisions in list(by_group.items())[:5]:
                print(f"  {group}: {len(provisions)} codes")

            return response.status_code == 200
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_enhanced_provision_api():
    """Test enhanced provision endpoint with all linked data"""
    print("\n" + "=" * 80)
    print("TEST 4: ENHANCED PROVISION API")
    print("=" * 80)

    test_provision_id = 1  # Adjust based on actual data
    url = f"{BASE_URL}/api/provisions/{test_provision_id}/enhanced"

    try:
        response = requests.get(url, timeout=5)
        print(f"\nEndpoint: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Response time: {data.get('meta', {}).get('responseTimeMs')}ms")

            enhanced = data.get('data', {})
            print(f"\nProvision {enhanced.get('refNumber')}:")
            print(f"  Category: {enhanced.get('provisionCategory')}")
            print(f"  Priority: {enhanced.get('displayPriority')}")
            print(f"  Mandatory: {enhanced.get('isMandatory')}")

            # Applicability
            app = enhanced.get('applicability', {})
            print(f"\nApplicability:")
            print(f"  Explicit zone: {app.get('explicitZone')}")
            print(f"  Applies to zone: {app.get('appliesToZone')}")
            print(f"  All zones: {app.get('appliesToAllZones')}")
            print(f"  State-wide: {app.get('appliesStateWide')}")
            print(f"  Source: {app.get('applicabilitySource')}")

            # Cross-references
            xrefs = enhanced.get('crossReferences', {})
            print(f"\nCross-references:")
            print(f"  Total: {xrefs.get('total')}")
            print(f"  Resolved: {xrefs.get('resolved')}")

            # Control codes
            codes = enhanced.get('controlCodes', {})
            print(f"\nControl codes:")
            print(f"  Total: {codes.get('total')}")
            print(f"  Code group: {codes.get('codeGroup')}")
            print(f"  Control type: {codes.get('controlType')}")
            print(f"  Individual codes: {codes.get('codes')}")

            return response.status_code == 200
        else:
            print(f"Error: {response.text}")
            return False

    except Exception as e:
        print(f"Error: {e}")
        return False


def test_performance():
    """Test query performance benchmarks"""
    print("\n" + "=" * 80)
    print("TEST 5: PERFORMANCE BENCHMARKS")
    print("=" * 80)

    tests = [
        ("Cross-references", f"{BASE_URL}/api/provisions/cross-references?provision_id=1"),
        ("Zone applicability", f"{BASE_URL}/api/provisions/zone-applicability?zone=R2&limit=50"),
        ("Control code search", f"{BASE_URL}/api/provisions/control-codes?code=C17"),
        ("Enhanced provision", f"{BASE_URL}/api/provisions/1/enhanced")
    ]

    all_fast = True

    for name, url in tests:
        try:
            start = datetime.now()
            response = requests.get(url, timeout=5)
            elapsed_ms = (datetime.now() - start).total_seconds() * 1000

            if response.status_code == 200:
                data = response.json()
                api_time = data.get('meta', {}).get('responseTimeMs', elapsed_ms)

                print(f"\n{name}:")
                print(f"  Total time: {elapsed_ms:.1f}ms")
                print(f"  API time: {api_time:.1f}ms")
                print(f"  Status: {'PASS' if api_time < 200 else 'SLOW'}")

                if api_time >= 200:
                    all_fast = False
            else:
                print(f"\n{name}: Failed (HTTP {response.status_code})")
                all_fast = False

        except Exception as e:
            print(f"\n{name}: Error - {e}")
            all_fast = False

    return all_fast


def run_all_tests():
    """Run all API tests"""
    print("Phase 2: API Integration Tests")
    print("=" * 80)
    print(f"Test run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")

    tests_passed = 0
    tests_total = 5

    if test_cross_references_api():
        tests_passed += 1

    if test_zone_applicability_api():
        tests_passed += 1

    if test_control_codes_api():
        tests_passed += 1

    if test_enhanced_provision_api():
        tests_passed += 1

    if test_performance():
        tests_passed += 1

    print("\n" + "=" * 80)
    print(f"VALIDATION COMPLETE: {tests_passed}/{tests_total} tests passed")
    print("=" * 80)

    if tests_passed == tests_total:
        print("\nPASS All API endpoints working correctly")
        print("Ready for frontend integration")
    else:
        print("\nWARNING Some tests failed - check Next.js server is running")


if __name__ == "__main__":
    run_all_tests()
