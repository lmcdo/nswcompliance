#!/usr/bin/env python3
"""
Test API Endpoints
Test the enhanced compliance API endpoints to verify integration
"""

import requests
import json
import time

def test_api_endpoints():
    """Test the enhanced compliance API endpoints"""
    
    base_url = "http://localhost:3001"
    
    # Test data - use a proper Inner West address  
    test_address = "1 Darling St, Balmain NSW 2041"
    test_proposal = {
        "height": 8.5,
        "fsr": 0.45,
        "front_setback": 6.0,
        "side_setback": 0.8,  # Should fail the 0.9m requirement
        "rear_setback": 5.5,   # Should fail the 6m requirement
        "development_type": "dwelling_house"
    }
    
    print("Testing Enhanced Compliance API")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    print(f"Test Address: {test_address}")
    print(f"Test Proposal: {json.dumps(test_proposal, indent=2)}")
    print()
    
    # Test 1: Property data endpoint
    print("1. Testing property data endpoint...")
    try:
        response = requests.get(f"{base_url}/api/property", params={"address": test_address})
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: Found property data for {data.get('address', 'unknown')}")
            print(f"   Former Council: {data.get('formerCouncilArea', 'unknown')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 2: Enhanced compliance check
    print("2. Testing enhanced compliance check...")
    try:
        # First get property data
        prop_response = requests.get(f"{base_url}/api/property", params={"address": test_address})
        if prop_response.status_code != 200:
            print(f"   Error: Could not get property data for compliance check")
            return
        
        prop_json = prop_response.json()
        property_data = prop_json["data"]  # Extract from wrapper
        
        payload = {
            "propertyData": property_data,
            "proposal": test_proposal,
            "formerCouncilArea": "Leichhardt",  # Known from setbacks test
            "useSemanticRules": True
        }
        
        response = requests.post(
            f"{base_url}/api/compliance/check",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: Compliance check completed")
            print(f"   Processing Method: {data.get('processing_method', 'unknown')}")
            print(f"   Results Count: {len(data.get('results', []))}")
            
            # Show some results
            for i, result in enumerate(data.get('results', [])[:3]):
                status = "PASS" if result.get('compliant') else "FAIL"
                print(f"     {i+1}. {status} - {result.get('requirement_type', 'unknown')}")
                if not result.get('compliant'):
                    print(f"        Gap: {result.get('gap', 0):.1f}")
                    print(f"        Required: {result.get('required_value', 'N/A')}")
                    print(f"        Proposed: {result.get('proposed_value', 'N/A')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    
    # Test 3: Setbacks API
    print("3. Testing setbacks API...")
    try:
        response = requests.get(f"{base_url}/api/compliance/setbacks", params={"address": test_address})
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: Setback rules retrieved")
            print(f"   Council Area: {data.get('formerCouncilArea', 'unknown')}")
            setbacks = data.get('setbacks', {})
            for setback_type, rules in setbacks.items():
                if isinstance(rules, dict):
                    distance = rules.get('distance', 'N/A')
                    print(f"     {setback_type.title()}: {distance}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print()
    print("=" * 50)
    print("API Testing Complete!")
    print()
    print("To test manually, visit:")
    print(f"  {base_url}/property/enhanced")

if __name__ == "__main__":
    # Wait a moment for server to be ready
    time.sleep(2)
    test_api_endpoints()