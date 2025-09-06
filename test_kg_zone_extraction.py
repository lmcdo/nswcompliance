#!/usr/bin/env python3
"""
Test KG Zone Extraction and Setback Integration
Direct test of the zone-setback mapping using KG entities
"""

import json
import requests
import time

def test_kg_setback_endpoint():
    print("TESTING KG-BASED ZONE SETBACK EXTRACTION")
    print("=" * 60)
    
    # Test with actual lot geometry from NSW API
    test_payload = {
        "property_id": 1962876,
        "lot_geometry": {
            "hasM": False,
            "hasZ": False,
            "rings": [[
                [16847736.627699625, -4009853.0436881627],
                [16847759.088035867, -4009853.2058471456],
                [16847759.408628315, -4009819.0692944797],
                [16847736.948292073, -4009818.9071354968],
                [16847736.627699625, -4009853.0436881627]
            ]],
            "spatialReference": {
                "wkid": 3857,
                "latestWkid": 3857
            }
        },
        "property_zone": "R2",  # Test with R2 zone (has 92 setback records)
        "lot_area": 350.5
    }
    
    print(f"Testing Zone: {test_payload['property_zone']}")
    print(f"Property ID: {test_payload['property_id']}")
    print(f"Lot Area: {test_payload['lot_area']} m²")
    
    try:
        print("\nCalling /api/setbacks/calculate...")
        start_time = time.time()
        
        response = requests.post(
            'http://localhost:3000/api/setbacks/calculate',
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        processing_time = time.time() - start_time
        print(f"API Response Time: {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("\nSETBACK CALCULATION SUCCESSFUL")
                
                setbacks = result.get('setback_results', [])
                buildable = result.get('buildable_area_analysis', {})
                
                print(f"\nSETBACK RESULTS FOUND: {len(setbacks)}")
                for setback in setbacks:
                    print(f"  - {setback.get('boundary_type', 'unknown')}: {setback.get('required_setback', 0)}m")
                    print(f"    Source: {setback.get('database_source', 'unknown')}")
                    print(f"    Confidence: {setback.get('confidence', 0):.2f}")
                    print(f"    Authority: {setback.get('authority_level', 'unknown')}")
                    print()
                
                print(f"BUILDABLE AREA ANALYSIS:")
                print(f"  - Total Lot Area: {buildable.get('total_lot_area', 0)} m²")
                print(f"  - Buildable Area: {buildable.get('buildable_area', 0)} m²")
                print(f"  - Buildable Percentage: {buildable.get('buildable_percentage', 0)}%")
                print(f"  - Setback Area Lost: {buildable.get('setback_area_lost', 0)} m²")
                
                if buildable.get('note'):
                    print(f"  - Note: {buildable['note']}")
                
                # Determine if KG extraction worked
                if len(setbacks) > 0:
                    kg_sources = [s for s in setbacks if 'KG' in s.get('reasoning', '') or 'kg' in s.get('database_source', '')]
                    if kg_sources:
                        print(f"\nKG EXTRACTION SUCCESS: {len(kg_sources)} KG-based setbacks found")
                    else:
                        print(f"\nFALLBACK EXTRACTION: {len(setbacks)} database setbacks found")
                else:
                    print(f"\nNO SETBACK DATA: Check KG zone entity extraction")
                
                print(f"\nProcessing Method: {result.get('processing_method', 'unknown')}")
                print(f"Precision Level: {result.get('precision_level', 'unknown')}")
                
            else:
                print(f"SETBACK CALCULATION FAILED: {result.get('error', 'Unknown error')}")
                
        else:
            print(f"API ERROR: Status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"REQUEST FAILED: {e}")
    except Exception as e:
        print(f"TEST FAILED: {e}")

def test_health_check():
    print("Testing setback calculation health check...")
    try:
        response = requests.get('http://localhost:3000/api/setbacks/calculate', timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"Health Status: {health.get('status', 'unknown')}")
            
            db_stats = health.get('database_stats', {})
            if db_stats:
                print(f"Database Stats:")
                for key, value in db_stats.items():
                    print(f"  - {key}: {value}")
        else:
            print(f"Health check failed: Status {response.status_code}")
    except Exception as e:
        print(f"Health check error: {e}")

if __name__ == "__main__":
    print("KG Zone Extraction Test")
    print("Target: http://localhost:3000")
    
    # Test health check first
    test_health_check()
    print()
    
    # Test KG setback extraction
    test_kg_setback_endpoint()
    
    print("=" * 60)
    print("KG Zone Extraction Test Complete")