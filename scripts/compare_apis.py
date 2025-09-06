#!/usr/bin/env python3
"""
API Comparison Tool - v0 vs v1
Tests both old working API and new v1 API to compare data completeness
"""

import requests
import json
import urllib.parse
from typing import Dict, Any, Optional

def test_nsw_planning_portal_direct(address: str) -> Optional[Dict[str, Any]]:
    """Test NSW Planning Portal API directly for baseline data"""
    
    try:
        # Step 1: Search for property
        encoded_address = urllib.parse.quote(address)
        search_url = f"https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address"
        search_params = {'a': address, 'noOfRecords': 1}
        
        print(f"Searching NSW Planning Portal for: {address}")
        search_response = requests.get(search_url, params=search_params, timeout=15)
        
        if search_response.status_code != 200:
            print(f"Search failed: {search_response.status_code}")
            return None
            
        search_data = search_response.json()
        if not search_data or len(search_data) == 0:
            print("No property found in search")
            return None
            
        property_info = search_data[0]
        prop_id = property_info.get('propId')
        
        if not prop_id:
            print("No propId found in search results")
            return None
            
        print(f"Found property ID: {prop_id}")
        
        # Step 2: Get planning layers
        layers_url = f"https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect"
        layers_params = {'type': 'property', 'id': prop_id, 'layers': 'epi'}
        
        layers_response = requests.get(layers_url, params=layers_params, timeout=15)
        layers_data = layers_response.json() if layers_response.status_code == 200 else []
        
        # Step 3: Get valuation data
        valuation_url = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation/MapServer/5/query"
        valuation_params = {
            'where': f'propid={prop_id}',
            'outFields': 'propid,address,val1_bd,val1_lv,prop_area,zone_desc,urbanity',
            'f': 'json'
        }
        
        valuation_response = requests.get(valuation_url, params=valuation_params, timeout=15)
        valuation_data = valuation_response.json() if valuation_response.status_code == 200 else {}
        
        return {
            'property_search': property_info,
            'planning_layers': layers_data,
            'valuation': valuation_data,
            'prop_id': prop_id
        }
        
    except Exception as e:
        print(f"NSW API error: {e}")
        return None

def analyze_nsw_data(nsw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze raw NSW data to extract property information"""
    
    if not nsw_data:
        return {}
    
    analysis = {
        'basic_info': {},
        'planning_constraints': {},
        'environmental': {},
        'data_availability': {}
    }
    
    # Extract basic property info
    valuation = nsw_data.get('valuation', {})
    if valuation.get('features') and len(valuation['features']) > 0:
        attrs = valuation['features'][0].get('attributes', {})
        analysis['basic_info'] = {
            'address': attrs.get('address', 'N/A'),
            'land_value': attrs.get('val1_lv', 'N/A'), 
            'valuation_date': attrs.get('val1_bd', 'N/A'),
            'property_area': attrs.get('prop_area', 'N/A'),
            'zone_description': attrs.get('zone_desc', 'N/A'),
            'urbanity': attrs.get('urbanity', 'N/A')
        }
    
    # Extract planning constraints from layers
    layers = nsw_data.get('planning_layers', [])
    constraints = {
        'fsr': 'Not found',
        'height': 'Not found', 
        'zone': 'Not found',
        'lot_size': 'Not found',
        'heritage': 'Not heritage listed',
        'lga': 'Not found'
    }
    
    for layer in layers:
        layer_name = layer.get('layerName', '')
        results = layer.get('results', [])
        
        if results and len(results) > 0:
            result = results[0]
            
            if 'Floor Space Ratio' in layer_name:
                fsr_value = result.get('Floor Space Ratio')
                constraints['fsr'] = fsr_value if fsr_value else 'No FSR control'
                constraints['lga'] = result.get('LGA Name', 'Unknown LGA')
                
            elif 'Height' in layer_name:
                height_value = result.get('Maximum Building Height') 
                constraints['height'] = height_value if height_value else 'No height limit'
                
            elif 'Zoning' in layer_name or 'Zone' in layer_name:
                zone_value = result.get('Zone')
                constraints['zone'] = zone_value if zone_value else 'Zone not specified'
                
            elif 'Lot Size' in layer_name:
                lot_size_value = result.get('Lot Size')
                constraints['lot_size'] = lot_size_value if lot_size_value else 'No minimum lot size'
                
            elif 'Heritage' in layer_name:
                constraints['heritage'] = 'Heritage listed'
                
    analysis['planning_constraints'] = constraints
    
    # Check data availability
    basic_fields = ['address', 'land_value', 'property_area', 'zone_description']
    constraint_fields = ['fsr', 'height', 'zone', 'lga']
    
    basic_available = sum(1 for field in basic_fields if analysis['basic_info'].get(field, 'N/A') != 'N/A')
    constraint_available = sum(1 for field in constraint_fields if constraints.get(field, 'Not found') not in ['Not found', 'N/A'])
    
    analysis['data_availability'] = {
        'basic_info_completeness': f"{basic_available}/{len(basic_fields)} fields",
        'planning_constraints_completeness': f"{constraint_available}/{len(constraint_fields)} fields",
        'total_layers_found': len(layers)
    }
    
    return analysis

def test_current_api(base_url: str, address: str) -> Optional[Dict[str, Any]]:
    """Test current local API endpoint"""
    
    try:
        url = f"{base_url}/api/compliance/setbacks"  # or whatever current endpoint exists
        params = {'address': address}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Current API failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Current API error: {e}")
        return None

def compare_apis(address: str):
    """Compare NSW direct API with current implementation"""
    
    print("API COMPARISON ANALYSIS")
    print("="*60)
    print(f"Testing address: {address}")
    print()
    
    # Test NSW Planning Portal directly
    print("1. Testing NSW Planning Portal directly...")
    nsw_data = test_nsw_planning_portal_direct(address)
    
    if nsw_data:
        print("SUCCESS: NSW Planning Portal API working")
        nsw_analysis = analyze_nsw_data(nsw_data)
    else:
        print("FAILED: NSW Planning Portal API not working")
        return
    
    print()
    print("NSW PLANNING PORTAL BASELINE DATA:")
    print("-" * 40)
    
    # Show basic property information
    basic_info = nsw_analysis.get('basic_info', {})
    print("Basic Property Info:")
    for key, value in basic_info.items():
        print(f"  {key}: {value}")
    
    print()
    print("Planning Constraints:")
    constraints = nsw_analysis.get('planning_constraints', {})
    for key, value in constraints.items():
        print(f"  {key}: {value}")
    
    print()
    print("Data Availability:")
    availability = nsw_analysis.get('data_availability', {})
    for key, value in availability.items():
        print(f"  {key}: {value}")
    
    # Save baseline data
    with open('nsw_api_baseline.json', 'w') as f:
        json.dump({
            'raw_data': nsw_data,
            'analysis': nsw_analysis,
            'address': address
        }, f, indent=2)
    
    print()
    print("BASELINE DATA SAVED to: nsw_api_baseline.json")
    print()
    print("KEY FINDINGS:")
    print("-" * 20)
    
    # Identify what should vs shouldn't be N/A
    genuine_na_fields = []
    should_have_data_fields = []
    
    for key, value in basic_info.items():
        if value not in ['N/A', 'Unknown', None, '']:
            should_have_data_fields.append(f"basic_info.{key}")
        else:
            genuine_na_fields.append(f"basic_info.{key}")
    
    for key, value in constraints.items():
        if value not in ['Not found', 'N/A', 'Unknown', None, '']:
            should_have_data_fields.append(f"constraints.{key}")
        else:
            genuine_na_fields.append(f"constraints.{key}")
    
    print(f"Fields that SHOULD have data: {len(should_have_data_fields)}")
    for field in should_have_data_fields[:10]:  # Show first 10
        print(f"  - {field}")
    
    print()
    print(f"Fields that are legitimately N/A: {len(genuine_na_fields)}")
    for field in genuine_na_fields[:5]:  # Show first 5
        print(f"  - {field}")
    
    return nsw_analysis

def main():
    """Main comparison function"""
    
    # Test with the provided address
    test_address = "3 Wilkinson Ln, Telopea NSW 2117, Australia"
    
    # Run comparison
    baseline_data = compare_apis(test_address)
    
    print()
    print("="*60)
    print("Next steps:")
    print("1. Use the baseline data to fix v1 API data mapping")
    print("2. Ensure v1 API returns real values for fields that have data")
    print("3. Only use N/A for fields that are genuinely not available")

if __name__ == "__main__":
    main()