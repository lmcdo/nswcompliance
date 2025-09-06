#!/usr/bin/env python3
"""Test API with different zones to validate end-to-end functionality"""

import requests
import json

# API endpoint
url = "http://localhost:8000/calculate-setbacks"

# Test real properties with known zones (based on the API logs)
test_properties = [
    {
        "name": "R2 Property (34 Pile Street - confirmed from API logs)",
        "data": {
            "address": "34 Pile Street, Dulwich Hill NSW 2203",
            "query_type": "setbacks"
        },
        "expected_zone": "R2",
        "expected_section": "Section 4.1"
    }
]

# Note: We'll use the known R2 property for now since we need real addresses
# that exist in the NSW Planning Portal for the API to work

print("Testing API with different zones...")
print("=" * 60)

for test in test_properties:
    print(f"\n{test['name']}")
    print(f"Expected zone: {test['expected_zone']}")
    print(f"Expected section: {test['expected_section']}")
    
    try:
        response = requests.post(url, json=test['data'], timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"API Response keys: {list(result.keys())}")
            
            # Look for regulatory pathway information
            if 'regulatory_pathway' in result:
                pathway = result['regulatory_pathway']
                sections = pathway.get('applicable_sections', [])
                print(f"Applicable sections: {sections}")
                
                # Validate zone-specific sections
                expected_zone = test['expected_zone']
                expected_section = test['expected_section']
                
                if sections == [expected_section]:
                    print(f"✅ PASS - {expected_zone} correctly mapped to {expected_section}")
                else:
                    print(f"❌ FAIL - Expected [{expected_section}], got {sections}")
                    
                # Show confidence score if available
                if 'confidence_score' in pathway:
                    print(f"Confidence: {pathway['confidence_score']}")
                    
            else:
                print("No regulatory pathway found in response")
                
            # Show setback results
            if 'setbacks' in result:
                setbacks = result['setbacks']
                print(f"Front setback: {setbacks.get('front', 'N/A')}")
                
            # Show basic property data
            if 'property_data' in result:
                prop_data = result['property_data']
                actual_zone = prop_data.get('zone', 'Unknown')
                print(f"Actual zone from API: {actual_zone}")
                
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

print("\n" + "=" * 60)
print("API zone testing completed.")