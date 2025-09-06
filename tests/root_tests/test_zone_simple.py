#!/usr/bin/env python3
"""Test zone-specific section extraction"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.universal_regulatory_engine import UniversalRegulatoryEngine

# Initialize engine
engine = UniversalRegulatoryEngine()

# Test zones and expected sections
test_data = [
    ('R2', 'Section 4.1'),
    ('R1', 'Section 4.2'), 
    ('R3', 'Section 4.2'),
    ('R4', 'Section 4.2'),
    ('B1', 'Section 5'),
    ('B2', 'Section 5'),
    ('B4', 'Section 5')
]

# Mock clause from boarding house data
mock_text = """Development applications for boarding houses in the R2 Low Density Residential zone will be assessed in accordance with the relevant controls in Section 4.1 of this DCP relating to low density residential development and the relevant objectives and controls in Section 4.3.

Development applications for boarding houses in the R1 General Residential, R3 Medium Density Residential and R4 High Density Residential zones will be assessed in accordance with the relevant controls in Section 4.2 of this DCP relating to multi dwelling housing and residential flat buildings and the relevant objectives and controls in Section 4.3.

Development applications for boarding houses in the B1 Neighbourhood Centre Zone; B2 Local Centre Zone and B4 Mixed Use zones will be assessed in accordance with the relevant controls in Section 5 of this DCP relating to commercial and mixed use development and the relevant objectives and controls in Section 4.3."""

print("Testing zone-specific section extraction...")
print("=" * 50)

for zone, expected in test_data:
    print(f"\nTesting {zone} (expect {expected})")
    
    try:
        sections = engine._extract_zone_specific_section_only(mock_text, zone)
        print(f"Got: {sections}")
        
        if len(sections) == 1 and sections[0] == expected:
            print("PASS")
        else:
            print(f"FAIL - Expected [{expected}], got {sections}")
    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 50)
print("Test completed.")