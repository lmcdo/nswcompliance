import pytest

"""
Real User Flow Test - Using Actual Planning Portal API

This test simulates the EXACT user experience:
1. User enters a real address (e.g., "10 Norton Street, Leichhardt NSW 2040")
2. App calls /api/property?address={address} which queries NSW Planning Portal
3. Planning Portal returns real property data (zone, heritage, council, etc.)
4. App uses that data to call /api/provisions/for-property
5. User sees their applicable provisions

This uses REAL NSW Planning Portal data, not mock data.
"""

import requests
import json
import sys
import time
from typing import Dict, Any

# Local dev server URL
API_BASE_URL = "http://localhost:3003/api"

# Real test addresses across all three councils
TEST_ADDRESSES = [
    {
        "address": "10 Norton Street, Leichhardt NSW 2040",
        "description": "Commercial/retail property in Norton St precinct"
    },
    {
        "address": "45 Terry Street, Rozelle NSW 2039",
        "description": "Residential property in Rozelle"
    },
    {
        "address": "25 Flood Street, Leichhardt NSW 2040",
        "description": "Residential near Norton Street"
    },
    {
        "address": "100 Stanmore Road, Stanmore NSW 2048",
        "description": "Property on main road in Stanmore (Marrickville)"
    },
    {
        "address": "52 Norton Street, Leichhardt NSW 2040",
        "description": "Norton Street retail/commercial"
    },
    {
        "address": "50 Liverpool Road, Ashfield NSW 2131",
        "description": "Commercial area in Ashfield"
    },
    {
        "address": "1 Metropolitan Road, Enmore NSW 2042",
        "description": "Residential property in Enmore (Marrickville)"
    },
]


def test_address_with_real_pp(address: str, description: str) -> Dict[str, Any]:
    """
    Test complete user flow with real Planning Portal data.

    Returns:
        Dict with test results including success status and provision counts
    """

    print("\n" + "="*80)
    print(f"Testing Address: {address}")
    print(f"Description: {description}")
    print("="*80)

    result = {
        "address": address,
        "success": False,
        "error": None,
        "pp_data": None,
        "provisions": None,
        "provision_count": 0
    }

    # STEP 1: Call Property API (queries Planning Portal)
    print("\n[STEP 1] Querying NSW Planning Portal via /api/property...")
    print(f"  Request: GET {API_BASE_URL}/property?address={address}")

    try:
        # Add timeout to avoid hanging on slow responses
        pp_response = requests.get(
            f"{API_BASE_URL}/property",
            params={"address": address},
            timeout=30
        )
        pp_response.raise_for_status()
        pp_data = pp_response.json()

        if not pp_data.get("success"):
            result["error"] = f"Property API returned success=false: {pp_data.get('error', 'Unknown error')}"
            print(f"  ERROR: {result['error']}")
            return result

        property_info = pp_data.get("data", {})
        result["pp_data"] = property_info

        # Extract zone from constraints (Planning Portal structure)
        constraints = property_info.get('constraints', {})
        zone = constraints.get('zone', 'N/A')
        zone_desc = constraints.get('zoneDescription', 'N/A')
        lga = constraints.get('lga', 'N/A')

        # Extract heritage info
        is_heritage = constraints.get('heritage', False)
        heritage_info = property_info.get('heritage', {})
        hca = heritage_info.get('heritageItemName', None) if is_heritage else None

        # Determine former council from suburb in address
        # Inner West Council is made up of: Ashfield, Marrickville, Leichhardt
        address_upper = address.upper()
        if any(suburb in address_upper for suburb in ['LEICHHARDT', 'ROZELLE', 'ANNANDALE', 'BALMAIN', 'LILYFIELD']):
            former_council = 'Leichhardt'
        elif any(suburb in address_upper for suburb in ['MARRICKVILLE', 'STANMORE', 'NEWTOWN', 'ENMORE', 'DULWICH HILL', 'ST PETERS']):
            former_council = 'Marrickville'
        elif any(suburb in address_upper for suburb in ['ASHFIELD', 'HABERFIELD', 'SUMMER HILL', 'LEWISHAM']):
            former_council = 'Ashfield'
        else:
            former_council = 'Unknown'

        # Display Planning Portal response
        print(f"\n  Planning Portal Response:")
        print(f"    Address: {property_info.get('address', 'N/A')}")
        print(f"    LGA: {lga}")
        print(f"    Former Council (derived): {former_council}")
        print(f"    Zone: {zone} - {zone_desc}")
        print(f"    Property Area: {property_info.get('propertyArea', 'N/A')}")
        print(f"    Land Value: {property_info.get('landValue', 'N/A')}")
        print(f"    Heritage Item: {is_heritage}")
        if hca:
            print(f"    HCA: {hca}")

        coords = property_info.get('coordinates', {})
        if coords:
            print(f"    Coordinates: ({coords.get('lat', 'N/A')}, {coords.get('lon', 'N/A')})")

        # Store derived fields for provisions query
        property_info['former_council'] = former_council
        property_info['zone'] = zone
        property_info['heritage'] = {'is_heritage_item': is_heritage, 'heritage_conservation_area': hca}

    except requests.exceptions.Timeout:
        result["error"] = "Planning Portal API timeout (>30s)"
        print(f"  ERROR: {result['error']}")
        return result
    except requests.exceptions.RequestException as e:
        result["error"] = f"Planning Portal API request failed: {str(e)}"
        print(f"  ERROR: {result['error']}")
        return result
    except Exception as e:
        result["error"] = f"Unexpected error querying Planning Portal: {str(e)}"
        print(f"  ERROR: {result['error']}")
        return result

    # Validate we got minimum required data
    if former_council == 'Unknown' or zone == 'N/A':
        result["error"] = f"Could not determine former_council ({former_council}) or zone ({zone})"
        print(f"  ERROR: {result['error']}")
        return result

    # STEP 2: Call Provisions API with Planning Portal data
    print("\n[STEP 2] Querying provisions API with Planning Portal data...")

    # Build provisions query params from derived Planning Portal data
    provisions_params = {
        "former_council": former_council,
        "zone": zone,
        "heritage": is_heritage
    }

    # Add HCA if present
    if hca:
        provisions_params["hca"] = hca

    print(f"  Request: GET {API_BASE_URL}/provisions/for-property")
    print(f"  Params: {json.dumps(provisions_params, indent=4)}")

    try:
        provisions_response = requests.get(
            f"{API_BASE_URL}/provisions/for-property",
            params=provisions_params,
            timeout=30
        )
        provisions_response.raise_for_status()
        provisions_data = provisions_response.json()

        if not provisions_data.get("success"):
            result["error"] = f"Provisions API returned success=false: {provisions_data.get('error', 'Unknown')}"
            print(f"  ERROR: {result['error']}")
            return result

        result["provisions"] = provisions_data

    except requests.exceptions.RequestException as e:
        result["error"] = f"Provisions API request failed: {str(e)}"
        print(f"  ERROR: {result['error']}")
        return result

    # STEP 3: Validate and Display Results
    print("\n[STEP 3] Provision Results")

    summary = provisions_data.get("data", {}).get("summary", {})
    total_provisions = summary.get("total_provisions", 0)
    result["provision_count"] = total_provisions

    print(f"\n  Total Provisions: {total_provisions}")

    if total_provisions == 0:
        result["error"] = "API returned 0 provisions (expected >0 for valid property)"
        print(f"  WARNING: {result['error']}")
        return result

    # Layer breakdown
    print(f"\n  Provisions by Layer:")
    print(f"    Generic (all properties):     {summary.get('layer_1_generic', 0)}")
    print(f"    Use-Specific (zone):          {summary.get('layer_2_use_specific', 0)}")
    print(f"    Condition (site features):    {summary.get('layer_3_condition', 0)}")
    print(f"    Precinct (location):          {summary.get('layer_4_precinct', 0)}")

    # Topic breakdown (top 5)
    by_topic = provisions_data.get("data", {}).get("by_topic", {})
    if by_topic:
        topic_counts = [(topic, len(provisions)) for topic, provisions in by_topic.items()]
        sorted_topics = sorted(topic_counts, key=lambda x: x[1], reverse=True)[:5]

        print(f"\n  Top Topics:")
        for topic, count in sorted_topics:
            print(f"    {topic}: {count}")

    # Show sample provisions
    by_layer = provisions_data.get("data", {}).get("by_layer", [])

    print(f"\n  Sample Provisions (first from each layer):")
    for layer_data in by_layer:
        layer_name = layer_data.get("layer_name", "Unknown")
        provisions = layer_data.get("provisions", [])

        if provisions:
            first_prov = provisions[0]
            text = first_prov.get("provision_text", "")
            truncated = text[:120] + "..." if len(text) > 120 else text
            print(f"\n    [{layer_name}]")
            print(f"    {truncated}")

    # Success!
    result["success"] = True
    print(f"\n  [SUCCESS] Retrieved {total_provisions} applicable provisions")

    return result


def main():
    """Run all real user flow tests with Planning Portal."""

    print("\n" + "="*80)
    print("REAL USER FLOW TEST - NSW PLANNING PORTAL INTEGRATION")
    print("="*80)
    print("\nThis test simulates the complete user experience:")
    print("  1. User enters real NSW address")
    print("  2. App queries NSW Planning Portal via /api/property")
    print("  3. Planning Portal returns property details (zone, heritage, council)")
    print("  4. App queries /api/provisions/for-property with that data")
    print("  5. User sees applicable provisions")
    print("\nUsing REAL Planning Portal data, not mocks.")

    # Check API server
    print("\n[PREFLIGHT] Checking API server...")
    try:
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"  API Status: {health.json().get('status', 'unknown')}")
    except:
        print(f"  ERROR: API server not responding at {API_BASE_URL}")
        print(f"  Start server: cd frontend-nextjs && npm run dev")
        sys.exit(1)

    # Run tests
    results = []

    for test_case in TEST_ADDRESSES:
        result = test_address_with_real_pp(
            test_case["address"],
            test_case["description"]
        )
        results.append(result)

        # Small delay between tests to avoid rate limiting
        time.sleep(2)

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if passed:
        print("\n[PASSED TESTS]")
        for r in passed:
            pp_data = r.get("pp_data", {})
            council = pp_data.get("former_council", "Unknown")
            zone = pp_data.get("zone", "Unknown")
            count = r.get("provision_count", 0)
            print(f"  [OK] {r['address']}")
            print(f"       Council: {council}, Zone: {zone}, Provisions: {count}")

    if failed:
        print("\n[FAILED TESTS]")
        for r in failed:
            print(f"  [X] {r['address']}")
            print(f"      Error: {r.get('error', 'Unknown error')}")

    # Statistics
    if passed:
        provision_counts = [r["provision_count"] for r in passed]
        avg_provisions = sum(provision_counts) / len(provision_counts)

        print(f"\n[STATISTICS]")
        print(f"  Average provisions per property: {avg_provisions:.0f}")
        print(f"  Min provisions: {min(provision_counts)}")
        print(f"  Max provisions: {max(provision_counts)}")

    # Exit code
    if len(passed) == len(results):
        print("\n[SUCCESS] ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n[FAILED] {len(failed)} TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()

_PROBE_URL = "http://localhost:3003"

# ── Live-server guard ────────────────────────────────────────────────────────
# This is a genuine integration test: it drives a running local server, not a
# pure function. It was quarantined on 2026-05-23 and became invisible, which
# is worse than being skipped — an uncollected file reports nothing at all.
#
# So instead of hiding it, it now SKIPS with a reason when the server is not
# up, and carries the `integration` marker so it stays out of the default run
# while remaining visible and runnable on demand:
#
#     pytest -m integration        (with the dev server running)
#
# The probe uses a short timeout and is evaluated once at import, so a missing
# server costs a fraction of a second rather than a hung suite.
def _server_is_up(url: str, timeout: float = 1.0) -> bool:
    try:
        import urllib.request
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _server_is_up(_PROBE_URL),
        reason=f"needs a local server at {_PROBE_URL} — start the dev server, then: pytest -m integration",
    ),
]
