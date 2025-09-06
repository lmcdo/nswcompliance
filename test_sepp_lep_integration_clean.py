#!/usr/bin/env python3
"""
Test SEPP-LEP Hierarchical Integration
Using NSW Planning API response template for comprehensive testing
"""

import json
import requests
import time
from datetime import datetime

# Load NSW API sample response (template)
def load_nsw_api_template():
    with open('nsw_api_sample_response.json', 'r') as f:
        return json.load(f)

# Test property data
TEST_PROPERTY = {
    "address": "36 Pile St, Dulwich Hill NSW 2203, Australia",
    "property_id": 1962876,
    "proposed_development": {
        "property_id": 1962876,
        "height": 8.5,  # Below LEP limit of 9.5m
        "fsr": 0.55,    # Below LEP limit of 0.6
        "lot_area": 350.5,
        "front_setback": 3.0,
        "side_setback": 1.2,
        "rear_setback": 6.0
    }
}

def test_compliance_assessment():
    print("Testing SEPP-LEP Hierarchical Integration")
    print("=" * 60)
    
    # Load NSW API template
    nsw_api_layers = load_nsw_api_template()
    print(f"Loaded NSW API template with {len(nsw_api_layers)} layers")
    
    # Identify SEPP layers
    sepp_layers = [layer for layer in nsw_api_layers if 
                   any(result.get('EPI Type') == 'SEPP' for result in layer.get('results', []))]
    print(f"Found {len(sepp_layers)} layers containing SEPP provisions")
    
    # Identify LEP layers
    lep_layers = [layer for layer in nsw_api_layers if 
                  any(result.get('EPI Type') == 'LEP' for result in layer.get('results', []))]
    print(f"Found {len(lep_layers)} layers containing LEP provisions")
    
    # Print SEPP provisions found
    print("\nSEPP PROVISIONS IDENTIFIED:")
    for layer in sepp_layers:
        if layer['layerName'] == 'Special Provisions':
            for result in layer['results']:
                if result.get('EPI Type') == 'SEPP':
                    print(f"   - {result.get('title', 'Unknown SEPP')}")
                    print(f"     Document: {result.get('EPI Name', 'N/A')}")
                    print(f"     Value: {result.get('Class', result.get('Label', 'N/A'))}")
    
    # Print LEP provisions found
    print("\nLEP PROVISIONS IDENTIFIED:")
    key_lep_layers = ['Land Zoning Map', 'Height of Buildings Map', 'Floor Space Ratio Map', 'Lot Size Map']
    for layer_name in key_lep_layers:
        layer = next((l for l in nsw_api_layers if l['layerName'] == layer_name), None)
        if layer and layer.get('results'):
            result = layer['results'][0]
            if result.get('EPI Type') == 'LEP':
                print(f"   - {layer_name}: {result.get('Zone', result.get('Floor Space Ratio', result.get('Lot Size', result.get('Maximum Building Height', 'N/A'))))}")
                print(f"     Source: {result.get('EPI Name', 'N/A')}")
                if result.get('Legislative Clause'):
                    print(f"     Clause: {result['Legislative Clause']}")
    
    # Prepare API request
    request_payload = {
        "property_address": TEST_PROPERTY["address"],
        "property_id": TEST_PROPERTY["property_id"],
        "nsw_api_layers": nsw_api_layers,
        "proposed_development": TEST_PROPERTY["proposed_development"]
    }
    
    print(f"\nTESTING HIERARCHICAL COMPLIANCE ASSESSMENT")
    print(f"Property: {TEST_PROPERTY['address']}")
    print(f"Proposed Development:")
    for key, value in TEST_PROPERTY["proposed_development"].items():
        if key != "property_id":
            print(f"   - {key}: {value}")
    
    # Test compliance assessment API
    try:
        print(f"\nCalling compliance assessment API...")
        start_time = time.time()
        
        response = requests.post(
            'http://localhost:3000/api/compliance/assess',
            json=request_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        processing_time = time.time() - start_time
        print(f"API Response Time: {processing_time:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                print("\n COMPLIANCE ASSESSMENT SUCCESSFUL")
                
                assessment = result.get('assessment', {})
                report = result.get('detailed_report', {})
                processing = result.get('hierarchical_processing', {})
                
                # Print hierarchical processing results
                print(f"\n HIERARCHICAL PROCESSING STATUS:")
                print(f"    SEPP Provisions Processed: {'' if processing.get('sepp_provisions_processed') else ''}")
                print(f"    LEP Provisions Processed: {'' if processing.get('lep_provisions_processed') else ''}")
                print(f"    Authority Hierarchy Applied: {'' if processing.get('authority_hierarchy_applied') else ''}")
                print(f"    Conflict Resolution Performed: {'' if processing.get('conflict_resolution_performed') else ''}")
                
                # Print assessment results
                print(f"\n COMPLIANCE ASSESSMENT RESULTS:")
                print(f"    Council Area: {assessment.get('council_area', 'N/A').title()}")
                print(f"    Zone: {assessment.get('zone', 'N/A')}")
                print(f"    Development Pathway: {assessment.get('development_pathway', 'N/A')}")
                print(f"    Compliance Confidence: {assessment.get('compliance_confidence', 0) * 100:.1f}%")
                print(f"    Professional Review Required: {'Yes' if assessment.get('professional_review_required') else 'No'}")
                
                # Print statutory compliance
                statutory = assessment.get('statutory_compliance', {})
                print(f"\n  STATUTORY COMPLIANCE:")
                if 'height' in statutory:
                    height = statutory['height']
                    print(f"    Height: {height.get('proposed', 0)}m (limit: {height.get('limit', 0)}m) - {' Compliant' if height.get('compliant') else ' Non-compliant'}")
                    print(f"     Source: {height.get('source', 'N/A')}")
                    print(f"     Authority: {height.get('legal_authority', 'N/A')}")
                    if height.get('hierarchical_justification'):
                        print(f"     Legal Basis: {height['hierarchical_justification']}")
                    if height.get('overridden_provisions'):
                        print(f"     Overrides: {', '.join(height['overridden_provisions'])}")
                
                # Print legal references
                legal_refs = assessment.get('legal_references', [])
                if legal_refs:
                    print(f"\n LEGAL REFERENCES:")
                    for i, ref in enumerate(legal_refs[:5], 1):  # Show first 5
                        print(f"   {i}. {ref}")
                
                # Print audit trail
                audit_trail = assessment.get('audit_trail', [])
                if audit_trail:
                    print(f"\n AUDIT TRAIL:")
                    for i, entry in enumerate(audit_trail[:3], 1):  # Show first 3
                        print(f"   {i}. {entry}")
                
                # Test metadata
                metadata = result.get('processing_metadata', {})
                print(f"\n PROCESSING METADATA:")
                print(f"    Processing Time: {metadata.get('processing_time_ms', 0)}ms")
                print(f"    Reliability Grade: {metadata.get('reliability_grade', 'N/A')}")
                print(f"    SEPP-LEP Integration: {metadata.get('sepp_lep_integration', 'N/A')}")
                
                print(f"\n TEST RESULT: SEPP-LEP Integration Working Successfully")
                
            else:
                print(f" ASSESSMENT FAILED: {result.get('error', 'Unknown error')}")
                
        else:
            print(f" API ERROR: Status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f" REQUEST FAILED: {e}")
    except Exception as e:
        print(f" TEST FAILED: {e}")

def test_health_check():
    print(f"\n Testing API Health Check")
    try:
        response = requests.get('http://localhost:3000/api/compliance/assess', timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f" API Health: {health.get('status', 'unknown')}")
            
            features = health.get('features', {})
            print(f" Features Enabled:")
            for feature, enabled in features.items():
                print(f"    {feature.replace('_', ' ').title()}: {'' if enabled else ''}")
                
            council_areas = health.get('council_areas', {})
            if council_areas:
                print(f"  Council Area Coverage:")
                for council, reliability in council_areas.items():
                    print(f"    {council.title()}: {reliability}")
        else:
            print(f" Health check failed: Status {response.status_code}")
    except Exception as e:
        print(f" Health check error: {e}")

if __name__ == "__main__":
    print(f" SEPP-LEP Hierarchical Integration Test")
    print(f" Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Target: http://localhost:3000")
    
    # Test health check first
    test_health_check()
    
    # Test full compliance assessment
    test_compliance_assessment()
    
    print(f"\n" + "="*60)
    print(f" SEPP-LEP Integration Test Complete")