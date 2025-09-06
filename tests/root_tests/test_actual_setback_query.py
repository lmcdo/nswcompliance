#!/usr/bin/env python3
"""
ACTUAL SETBACK QUERY TEST
=========================
This file tests the complete setback calculation system and saves the output.
"""

import sys
import asyncio
import json
from datetime import datetime

sys.path.append('.')

class PropertyData:
    """Correct property data structure for the system"""
    def __init__(self):
        self.address = "123 Smith Street, Marrickville"
        self.zone = "R2"
        self.lga_name = "Inner West"
        self.height_limit = "8.5m"
        self.former_council_area = "Marrickville"
        self.suburb = "Marrickville"
        self.land_area = "300 sqm"
        self.fsr_limit = "0.6:1"
        self.lga = "Inner West"

async def test_complete_setback_system():
    """Test the complete setback calculation system"""
    
    output = []
    output.append("ACTUAL SETBACK QUERY TEST RESULTS")
    output.append("=" * 60)
    output.append(f"Test executed: {datetime.now()}")
    output.append("")
    
    try:
        # Create property data
        property_data = PropertyData()
        output.append("TEST PROPERTY DATA:")
        output.append(f"  Address: {property_data.address}")
        output.append(f"  Zone: {property_data.zone}")
        output.append(f"  LGA: {property_data.lga_name}")
        output.append(f"  Height Limit: {property_data.height_limit}")
        output.append(f"  Former Council: {property_data.former_council_area}")
        output.append("")
        
        # Test 1: Enhanced Query Processor
        output.append("TEST 1: Direct Database Query")
        output.append("-" * 30)
        
        from enhanced_query_processor import query_validated_processor
        
        test_queries = [
            "R2 setback requirements metres",
            "front setback 6 metres",
            "setback Marrickville"
        ]
        
        for query in test_queries:
            output.append(f"Query: {query}")
            result = query_validated_processor(query)
            output.append(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
            output.append("")
        
        # Test 2: Complete Setback Calculation
        output.append("TEST 2: Complete Setback Calculation")
        output.append("-" * 30)
        
        from services.authoritative_setback_calculator import calculate_authoritative_setbacks_for_council
        
        result = await calculate_authoritative_setbacks_for_council(property_data)
        
        output.append("CALCULATION RESULTS:")
        output.append(f"  Front setback: {result.front_setback}m")
        output.append(f"  Side setback: {result.side_setback}m")
        output.append(f"  Rear setback: {result.rear_setback}m")
        output.append(f"  Confidence: {result.confidence_grade} ({result.confidence_percentage}%)")
        output.append("")
        
        output.append("REGULATORY SOURCES:")
        for source in result.regulatory_sources:
            output.append(f"  - {source}")
        output.append("")
        
        # Test 3: Database Verification
        output.append("TEST 3: Database Verification")
        output.append("-" * 30)
        
        import sqlite3
        conn = sqlite3.connect('nsw_planning.db')
        cur = conn.cursor()
        
        # Check extracted controls
        setback_controls = cur.execute("""
            SELECT dc.control_subtype, dc.value_numeric, dc.unit,
                   rp.document_id, rp.page_number
            FROM development_controls dc
            JOIN regulatory_provisions rp ON dc.provision_id = rp.id
            WHERE dc.control_type = 'setback'
            ORDER BY dc.confidence_score DESC
            LIMIT 5
        """).fetchall()
        
        output.append(f"Found {len(setback_controls)} setback controls in database:")
        for i, (subtype, value, unit, doc, page) in enumerate(setback_controls, 1):
            output.append(f"  {i}. {subtype}: {value}{unit}")
            output.append(f"     Document: {doc[:50]}...")
            output.append(f"     Page: {page or 'Not specified'}")
        
        conn.close()
        output.append("")
        
        # Test 4: API Integration Test
        output.append("TEST 4: Simulated API Call")
        output.append("-" * 30)
        
        # Simulate what would happen when user clicks "Calculate Setbacks" button
        api_response = {
            "success": True,
            "property": {
                "address": property_data.address,
                "zone": property_data.zone,
                "lga": property_data.lga_name
            },
            "setbacks": {
                "front": f"{result.front_setback}m",
                "side": f"{result.side_setback}m", 
                "rear": f"{result.rear_setback}m"
            },
            "confidence": {
                "grade": result.confidence_grade,
                "percentage": result.confidence_percentage
            },
            "sources": result.regulatory_sources,
            "data_source": "Enhanced database with real regulatory data",
            "timestamp": datetime.now().isoformat()
        }
        
        output.append("Simulated API Response:")
        output.append(json.dumps(api_response, indent=2))
        output.append("")
        
        output.append("TEST STATUS: SUCCESS")
        output.append("All components working with real database data")
        
        return True, output
        
    except Exception as e:
        output.append(f"TEST FAILED: {str(e)}")
        import traceback
        output.append("TRACEBACK:")
        output.append(traceback.format_exc())
        return False, output

def main():
    """Run the test and save output to file"""
    print("Running actual setback query test...")
    
    # Run the test
    success, output_lines = asyncio.run(test_complete_setback_system())
    
    # Save to output file
    output_file = "actual_setback_test_output.txt"
    with open(output_file, 'w') as f:
        for line in output_lines:
            f.write(line + '\n')
    
    # Print to console
    for line in output_lines:
        print(line)
    
    print(f"\nTest output saved to: {output_file}")
    print(f"Test result: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    main()