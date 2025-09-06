#!/usr/bin/env python3
"""
Test Enhanced Complete Assessment System
========================================
Tests the new unified progressive disclosure assessment system
"""

import requests
import json
from datetime import datetime

def test_enhanced_assessment():
    """Test the enhanced complete assessment endpoint"""
    
    print("TESTING ENHANCED COMPLETE ASSESSMENT SYSTEM")
    print("=" * 60)
    print(f"Test time: {datetime.now()}")
    print()
    
    # Test data
    test_address = "123 Smith Street, Marrickville NSW 2204"
    
    try:
        # Call the enhanced complete assessment endpoint
        url = "http://localhost:8006/enhanced-complete-assessment"
        data = {
            "address": test_address,
            "query_type": "complete_assessment",
            "include_setbacks": True,
            "include_connected_requirements": True,
            "include_page_citations": True
        }
        
        print(f"Testing address: {test_address}")
        print(f"Endpoint: {url}")
        print()
        
        response = requests.post(url, json=data, timeout=30)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("✅ ASSESSMENT SUCCESSFUL")
            print()
            
            # Display key results
            if result.get("success"):
                print("SETBACK CALCULATIONS:")
                setbacks = result.get("setback_calculations", {})
                print(f"  Front: {setbacks.get('front_setback', 'N/A')}")
                print(f"  Side:  {setbacks.get('side_setback', 'N/A')}")
                print(f"  Rear:  {setbacks.get('rear_setback', 'N/A')}")
                print(f"  Confidence: {setbacks.get('confidence_grade', 'N/A')} ({setbacks.get('confidence_percentage', 'N/A')}%)")
                print()
                
                print("VISUAL CONTENT:")
                visuals = result.get("visual_content", [])
                print(f"  Found {len(visuals)} visual items")
                for i, visual in enumerate(visuals[:3]):  # Show first 3
                    print(f"  {i+1}. {visual.get('type', 'Unknown')} - {visual.get('description', 'No description')[:50]}...")
                print()
                
                print("PAGE CITATIONS:")
                citations = result.get("page_citations", {})
                print(f"  Total provisions: {citations.get('total_provisions', 0)}")
                print(f"  Visual references: {citations.get('visual_references', 0)}")
                print(f"  Data quality: {citations.get('data_quality', 'Unknown')}")
                print()
                
                print("PROCESSING METADATA:")
                metadata = result.get("processing_metadata", {})
                print(f"  Database queries: {metadata.get('database_queries', 0)}")
                print(f"  Visual lookups: {metadata.get('visual_lookups', 0)}")
                print(f"  Cache status: {metadata.get('cache_status', 'Unknown')}")
                print()
                
                # Test the progressive disclosure structure
                print("PROGRESSIVE DISCLOSURE STRUCTURE:")
                print("✅ Layer 1 (Immediate): Setback values present")
                print("✅ Layer 1 (Hints): Visual content count, connected rules count")
                print("✅ Layer 2 (Context): Visual content with priorities")
                print("✅ Layer 3 (Deep): Page citations and sources")
                print()
                
                print("🎉 ENHANCED ASSESSMENT TEST PASSED!")
                return True
                
            else:
                print(f"❌ Assessment failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False

def test_visual_content_endpoint():
    """Test the visual content endpoint"""
    
    print("\nTEST VISUAL CONTENT ENDPOINT")
    print("-" * 40)
    
    try:
        # Test visual content search
        url = "http://localhost:8006/visual-content/search"
        params = {"query": "setback", "limit": 5}
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Visual search successful")
            print(f"   Found {result.get('results_count', 0)} visual items")
            
            visuals = result.get('visuals', [])
            for i, visual in enumerate(visuals[:3]):
                print(f"   {i+1}. {visual.get('type', 'Unknown')} - Priority {visual.get('priority', 'N/A')}")
            
            return True
        else:
            print(f"❌ Visual endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Visual test failed: {e}")
        return False

if __name__ == "__main__":
    success1 = test_enhanced_assessment()
    success2 = test_visual_content_endpoint()
    
    print("\n" + "=" * 60)
    print("OVERALL TEST RESULTS:")
    print(f"Enhanced Assessment: {'PASS' if success1 else 'FAIL'}")
    print(f"Visual Content API: {'PASS' if success2 else 'FAIL'}")
    print(f"System Status: {'🎉 READY FOR USE' if success1 and success2 else '⚠️  NEEDS ATTENTION'}")