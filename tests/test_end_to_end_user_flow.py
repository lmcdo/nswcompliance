"""
End-to-End User Flow Test

Simulates the complete user journey:
1. User enters an address
2. App calls Planning Portal API to get property details
3. App uses those details to query provisions API
4. User sees the provisions that apply to their property

Tests with REAL addresses from all three councils (Ashfield, Marrickville, Leichhardt)
"""

import requests
import json
import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Test addresses from each council
TEST_ADDRESSES = [
    {
        "address": "10 Norton Street, Leichhardt NSW 2040",
        "expected_council": "Leichhardt",
        "description": "Commercial precinct in Leichhardt"
    },
    {
        "address": "45 Terry Street, Rozelle NSW 2039",
        "expected_council": "Leichhardt",
        "description": "Residential property in Rozelle (Leichhardt)"
    },
    {
        "address": "25 Flood Street, Leichhardt NSW 2040",
        "expected_council": "Leichhardt",
        "description": "Residential near Norton Street"
    },
    {
        "address": "100 Stanmore Road, Stanmore NSW 2048",
        "expected_council": "Marrickville",
        "description": "Main road property in Stanmore"
    },
    {
        "address": "50 Liverpool Road, Ashfield NSW 2131",
        "expected_council": "Ashfield",
        "description": "Commercial area in Ashfield"
    }
]

# Local dev server URL
API_BASE_URL = "http://localhost:3003/api"

# Planning Portal API (using mock for now - replace with real endpoint)
PLANNING_PORTAL_URL = "https://api.planning.nsw.gov.au/property"


def call_planning_portal(address: str) -> Dict[str, Any]:
    """
    Call Planning Portal API to get property details.

    For testing purposes, this simulates the response since we may not have
    real Planning Portal API credentials in dev.

    In production, this would call:
    GET https://api.planning.nsw.gov.au/property/search?address={address}
    """

    # For testing, extract council from address and simulate response
    # In production, this would be real API call

    if "Leichhardt" in address or "Rozelle" in address or "Annandale" in address:
        council = "Leichhardt"
        zone = "R2"  # Common residential zone
    elif "Stanmore" in address or "Marrickville" in address or "Newtown" in address:
        council = "Marrickville"
        zone = "R2"
    elif "Ashfield" in address or "Haberfield" in address:
        council = "Ashfield"
        zone = "R2"
    else:
        council = "Unknown"
        zone = "R2"

    # Simulate Planning Portal response structure
    return {
        "success": True,
        "data": {
            "address": address,
            "former_council": council,
            "zone": zone,
            "heritage": {
                "is_heritage_item": False,
                "heritage_conservation_area": None,
                "items": []
            },
            "lot_size_sqm": 450,
            "coordinates": {
                "lat": -33.8823,
                "lng": 151.1577
            }
        }
    }


def call_provisions_api(property_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call our provisions API with property details from Planning Portal.
    """
    params = {
        "former_council": property_data["data"]["former_council"],
        "zone": property_data["data"]["zone"],
        "heritage": property_data["data"]["heritage"]["is_heritage_item"]
    }

    # Add HCA if present
    if property_data["data"]["heritage"]["heritage_conservation_area"]:
        params["hca"] = property_data["data"]["heritage"]["heritage_conservation_area"]

    url = f"{API_BASE_URL}/provisions/for-property"

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }


def format_user_response(provisions_data: Dict[str, Any]) -> str:
    """
    Format the provisions data as it would be shown to the user.
    """
    if not provisions_data.get("success"):
        return f"ERROR: {provisions_data.get('error', 'Unknown error')}"

    data = provisions_data.get("data", {})
    summary = data.get("summary", {})

    output = []
    output.append("\n" + "="*70)
    output.append("YOUR PROPERTY REQUIREMENTS")
    output.append("="*70)

    output.append(f"\nTotal provisions: {summary.get('total_provisions', 0)}")

    # Layer breakdown
    output.append("\nProvisions by layer:")
    output.append(f"  - General Requirements:        {summary.get('layer_1_generic', 0)}")
    output.append(f"  - Zone-Specific Requirements:  {summary.get('layer_2_use_specific', 0)}")
    output.append(f"  - Site Condition Requirements: {summary.get('layer_3_condition', 0)}")
    output.append(f"  - Precinct Requirements:       {summary.get('layer_4_precinct', 0)}")

    # Topic breakdown (top 5)
    by_topic = data.get("by_topic", {})
    if by_topic:
        output.append("\nTop topics:")
        # by_topic structure: {topic_name: [provisions]}
        topic_counts = [(topic, len(provisions)) for topic, provisions in by_topic.items()]
        sorted_topics = sorted(topic_counts, key=lambda x: x[1], reverse=True)[:5]
        for topic, count in sorted_topics:
            output.append(f"  - {topic}: {count}")

    # Sample provisions from each layer
    by_layer = data.get("by_layer", [])

    for layer_data in by_layer:
        layer_name = layer_data.get("layer_name", "Unknown")
        provisions = layer_data.get("provisions", [])

        if provisions:
            output.append(f"\n{layer_name} (showing first 3):")
            for i, prov in enumerate(provisions[:3], 1):
                text = prov.get("provision_text", "")
                truncated = text[:150] + "..." if len(text) > 150 else text
                output.append(f"  {i}. {truncated}")

    output.append("\n" + "="*70)

    return "\n".join(output)


def run_end_to_end_test(address_data: Dict[str, str]) -> bool:
    """
    Run complete end-to-end test for one address.

    Returns True if test passed, False if failed.
    """
    print("\n" + "="*70)
    print(f"Testing: {address_data['address']}")
    print(f"Description: {address_data['description']}")
    print("="*70)

    # Step 1: Call Planning Portal
    print("\n[STEP 1] Calling Planning Portal API...")
    property_data = call_planning_portal(address_data['address'])

    if not property_data.get("success"):
        print(f"FAILED: Planning Portal error: {property_data.get('error')}")
        return False

    print(f"  Council: {property_data['data']['former_council']}")
    print(f"  Zone: {property_data['data']['zone']}")
    print(f"  Heritage: {property_data['data']['heritage']['is_heritage_item']}")

    # Verify expected council
    if property_data['data']['former_council'] != address_data['expected_council']:
        print(f"WARNING: Expected {address_data['expected_council']}, got {property_data['data']['former_council']}")

    # Step 2: Call Provisions API
    print("\n[STEP 2] Calling Provisions API...")
    provisions_data = call_provisions_api(property_data)

    if not provisions_data.get("success"):
        print(f"FAILED: Provisions API error: {provisions_data.get('error')}")
        return False

    summary = provisions_data['data']['summary']
    total = summary.get('total_provisions', 0)

    print(f"  Total provisions returned: {total}")

    # Step 3: Validate response
    print("\n[STEP 3] Validating response...")

    if total == 0:
        print("FAILED: API returned 0 provisions")
        return False

    if total < 50:
        print(f"WARNING: Only {total} provisions (expected more for typical property)")

    # Check that at least one layer has provisions
    layers_with_data = sum(1 for layer in provisions_data['data']['by_layer'] if layer['count'] > 0)
    if layers_with_data == 0:
        print("FAILED: No provisions in any layer")
        return False

    print(f"PASSED: {total} provisions across {layers_with_data} layers")

    # Step 4: Format user response
    print("\n[STEP 4] Formatting user response...")
    user_output = format_user_response(provisions_data)
    print(user_output)

    return True


def main():
    """Run all end-to-end tests."""

    print("\n" + "="*70)
    print("END-TO-END USER FLOW TESTING")
    print("="*70)
    print("\nThis test simulates the complete user journey:")
    print("  1. User enters address")
    print("  2. Planning Portal API returns property details")
    print("  3. Provisions API returns applicable requirements")
    print("  4. User sees formatted response")

    # Check if API server is running
    print("\n[PREFLIGHT] Checking if API server is running...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        print(f"  API server status: OK")
    except:
        print(f"  ERROR: API server not responding at {API_BASE_URL}")
        print(f"  Please start the dev server: cd frontend-nextjs && npm run dev")
        sys.exit(1)

    # Run tests
    results = []

    for address_data in TEST_ADDRESSES:
        passed = run_end_to_end_test(address_data)
        results.append({
            "address": address_data["address"],
            "passed": passed
        })

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"  [{status}] {result['address']}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\nALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n{total_count - passed_count} TESTS FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
