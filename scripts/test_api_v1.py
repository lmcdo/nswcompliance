#!/usr/bin/env python3
"""
Test script for API v1 property endpoint
Tests the new comprehensive property data API with the provided address
"""

import requests
import json
import sys
from typing import Dict, Any

def test_property_api_v1(base_url: str, address: str) -> Dict[str, Any]:
    """Test the v1 property API endpoint"""
    
    url = f"{base_url}/api/v1/property"
    params = {'address': address}
    
    print(f"Testing API v1 with address: {address}")
    print(f"URL: {url}")
    print(f"Params: {params}")
    print("-" * 60)
    
    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ API Response successful")
            return data
        else:
            print(f"✗ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return {}
            
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
        return {}

def analyze_response(data: Dict[str, Any]) -> None:
    """Analyze the API response for completeness and accuracy"""
    
    if not data:
        print("No data to analyze")
        return
    
    print("\n" + "="*60)
    print("API v1 RESPONSE ANALYSIS")
    print("="*60)
    
    # Check basic structure
    if 'success' in data and data['success']:
        print("✓ API call successful")
    else:
        print("✗ API call failed")
        return
    
    if 'version' in data:
        print(f"✓ API Version: {data['version']}")
    
    # Analyze property data
    property_data = data.get('data', {})
    
    print(f"\n📍 PROPERTY INFORMATION:")
    print(f"   Address: {property_data.get('address', 'N/A')}")
    print(f"   Property ID: {property_data.get('propId', 'N/A')}")
    print(f"   LGA: {property_data.get('lga', 'N/A')}")
    print(f"   Property Type: {property_data.get('propertyType', 'N/A')}")
    
    print(f"\n🏘️  PLANNING CONTROLS:")
    print(f"   Zone: {property_data.get('zoneDescription', 'N/A')}")
    print(f"   Minimum Lot Size: {property_data.get('minimumLotSize', 'N/A')}")
    print(f"   Floor Space Ratio: {property_data.get('floorSpaceRatio', 'N/A')}")
    print(f"   Height Limit: {property_data.get('heightOfBuildings', 'N/A')}")
    
    print(f"\n🏛️  HERITAGE:")
    print(f"   Heritage Status: {property_data.get('heritageItem', 'N/A')}")
    if property_data.get('heritageDetails'):
        heritage = property_data['heritageDetails']
        print(f"   Heritage Type: {heritage.get('heritageType', 'N/A')}")
    
    print(f"\n🌿 ENVIRONMENTAL CONSTRAINTS:")
    print(f"   Bushfire Status: {property_data.get('bushfireProneStatus', 'N/A')}")
    print(f"   Flood Status: {property_data.get('floodProneStatus', 'N/A')}")
    print(f"   Acid Sulfate Soils: {property_data.get('acidSulfateSoils', 'N/A')}")
    
    print(f"\n🌳 INFRASTRUCTURE & ENVIRONMENT:")
    print(f"   Tree Canopy: {property_data.get('treeCanopyCover', 'N/A')}")
    print(f"   Mine Subsidence: {property_data.get('mineSubsidence', 'N/A')}")
    
    print(f"\n📋 PLANNING INSTRUMENTS:")
    print(f"   Regional Plan: {property_data.get('regionalPlan', 'N/A')}")
    print(f"   LEP: {property_data.get('planningInstrument', 'N/A')}")
    print(f"   DCP: {property_data.get('developmentControlPlan', 'N/A')}")
    
    # Check data quality
    data_quality = property_data.get('dataQuality', {})
    print(f"\n📊 DATA QUALITY:")
    print(f"   Completeness: {data_quality.get('completeness', 0)}%")
    print(f"   Confidence: {data_quality.get('confidence', 'N/A')}")
    print(f"   Data Sources: {len(data_quality.get('dataSources', []))} sources")
    
    # Count non-N/A fields
    na_count = 0
    total_count = 0
    
    key_fields = [
        'address', 'lga', 'zoneDescription', 'minimumLotSize', 
        'floorSpaceRatio', 'heightOfBuildings', 'heritageItem',
        'bushfireProneStatus', 'floodProneStatus', 'acidSulfateSoils',
        'treeCanopyCover', 'mineSubsidence', 'regionalPlan',
        'planningInstrument', 'developmentControlPlan'
    ]
    
    for field in key_fields:
        total_count += 1
        value = property_data.get(field, 'N/A')
        if value == 'N/A' or value == 'Unknown' or not value:
            na_count += 1
    
    data_completeness = ((total_count - na_count) / total_count) * 100
    
    print(f"\n📈 FIELD ANALYSIS:")
    print(f"   Fields with data: {total_count - na_count}/{total_count}")
    print(f"   Data completeness: {data_completeness:.1f}%")
    
    if na_count == 0:
        print("✓ All key fields have data - no inappropriate N/A values!")
    elif na_count <= 2:
        print("✓ Most fields populated - only genuine N/A values remain")
    else:
        print("⚠ Some fields still showing N/A - may need additional data sources")

def main():
    """Main test function"""
    
    # Configuration
    BASE_URL = "http://localhost:3000"  # Adjust as needed
    TEST_ADDRESS = "3 Wilkinson Ln, Telopea NSW 2117, Australia"
    
    print("NSW PROPERTY COMPLIANCE API v1 TEST")
    print("=" * 60)
    print(f"Testing with: {TEST_ADDRESS}")
    
    # Run the test
    response_data = test_property_api_v1(BASE_URL, TEST_ADDRESS)
    
    # Analyze the response
    analyze_response(response_data)
    
    # Save response for inspection
    if response_data:
        with open('api_v1_test_response.json', 'w') as f:
            json.dump(response_data, f, indent=2)
        print(f"\n💾 Full response saved to: api_v1_test_response.json")
    
    print(f"\n{'='*60}")
    print("Test completed!")

if __name__ == "__main__":
    main()