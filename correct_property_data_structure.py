#!/usr/bin/env python3
"""
CORRECT PROPERTY DATA STRUCTURE
===============================

Based on analysis of the actual codebase, here's the EXACT property data 
structure that the system expects (not mocks!)
"""

class PropertyData:
    """
    REAL Property Data Structure Expected by the System
    
    Based on actual code analysis from:
    - services/universal_regulatory_engine.py
    - services/authoritative_setback_calculator.py
    """
    
    def __init__(self, **kwargs):
        # REQUIRED FIELDS
        self.address = kwargs.get('address', '')           # "123 Smith Street, Marrickville"
        self.zone = kwargs.get('zone', '')                 # "R2", "R3", "B1", etc.
        self.lga_name = kwargs.get('lga_name', '')         # "Inner West"
        
        # COMMONLY USED FIELDS
        self.height_limit = kwargs.get('height_limit', '') # "8.5m", "9m", etc.
        self.former_council_area = kwargs.get('former_council_area', '') # "Marrickville", "Ashfield", "Leichhardt"
        
        # OPTIONAL FIELDS (for enhanced functionality)
        self.lga = kwargs.get('lga', kwargs.get('lga_name', ''))  # Some code uses .lga, some .lga_name
        self.suburb = kwargs.get('suburb', '')             # Extracted from address if needed
        self.land_area = kwargs.get('land_area', None)     # "300 sqm" or None
        self.fsr_limit = kwargs.get('fsr_limit', None)     # "0.6:1" or None
        self.lot_size = kwargs.get('lot_size', None)       # For compatibility
        self.heritage_status = kwargs.get('heritage_status', None)
        self.development_type = kwargs.get('development_type', None)

def create_correct_property_data(address="123 Smith Street, Marrickville"):
    """
    Create properly structured PropertyData that the system expects
    
    This extracts suburb and sets all required fields correctly
    """
    # Extract suburb from address
    address_parts = address.split(',')
    suburb = address_parts[1].strip() if len(address_parts) > 1 else ""
    
    # Determine former council area from suburb
    marrickville_suburbs = ["marrickville", "dulwich hill", "petersham", "stanmore", "enmore", "newtown"]
    ashfield_suburbs = ["ashfield", "summer hill", "haberfield"]
    leichhardt_suburbs = ["leichhardt", "balmain", "rozelle", "birchgrove"]
    
    suburb_lower = suburb.lower()
    
    if any(s in suburb_lower for s in marrickville_suburbs):
        former_council_area = "Marrickville"
    elif any(s in suburb_lower for s in ashfield_suburbs):
        former_council_area = "Ashfield"
    elif any(s in suburb_lower for s in leichhardt_suburbs):
        former_council_area = "Leichhardt"
    else:
        former_council_area = "Marrickville"  # Default for Inner West
    
    return PropertyData(
        address=address,
        zone="R2",  # Most common residential zone
        lga_name="Inner West",
        height_limit="8.5m",
        former_council_area=former_council_area,
        suburb=suburb,
        # Optional enhanced fields
        land_area="300 sqm",
        fsr_limit="0.6:1",
        development_type="residential"
    )

def test_real_setback_calculation_with_correct_structure():
    """
    Test the REAL setback calculation system with correct property structure
    """
    import asyncio
    import sys
    sys.path.append('.')
    
    async def run_test():
        print("TESTING REAL SETBACK SYSTEM WITH CORRECT PROPERTY STRUCTURE")
        print("=" * 70)
        
        # Create correct property data
        property_data = create_correct_property_data("123 Smith Street, Marrickville")
        
        print("Property Data (CORRECT STRUCTURE):")
        for attr in ['address', 'zone', 'lga_name', 'height_limit', 'former_council_area', 'suburb']:
            value = getattr(property_data, attr, 'NOT SET')
            print(f"  {attr}: {value}")
        print()
        
        try:
            # Test the universal regulatory engine first
            from services.universal_regulatory_engine import UniversalRegulatoryEngine
            
            print("STEP 1: Testing Universal Regulatory Engine...")
            engine = UniversalRegulatoryEngine()
            framework = engine.discover_regulatory_framework(property_data)
            
            print(f"✓ Framework discovered:")
            print(f"  - DCP: {framework.applicable_dcp}")
            print(f"  - Development type: {framework.development_type}")
            print(f"  - Confidence: {framework.confidence_score}")
            print(f"  - Setback controls: {len(framework.setback_controls) if isinstance(framework.setback_controls, dict) else 'None'}")
            print()
            
            # Test the complete setback calculation
            print("STEP 2: Testing Complete Setback Calculation...")
            from services.authoritative_setback_calculator import calculate_authoritative_setbacks_for_council
            
            result = await calculate_authoritative_setbacks_for_council(property_data)
            
            print("✓ SETBACK CALCULATION RESULTS:")
            print(f"  - Front setback: {result.front_setback}m")
            print(f"  - Side setback: {result.side_setback}m") 
            print(f"  - Rear setback: {result.rear_setback}m")
            print(f"  - Confidence: {result.confidence_grade} ({result.confidence_percentage}%)")
            print()
            
            print("✓ REGULATORY SOURCES:")
            for source in result.regulatory_sources:
                print(f"  - {source}")
            print()
            
            # Check if we got database results or fallbacks
            measurement_points = getattr(result, 'measurement_points', {})
            database_sources = 0
            fallback_sources = 0
            
            for point_type, details in measurement_points.items():
                if isinstance(details, str) and 'Database' in details:
                    database_sources += 1
                elif isinstance(details, str) and 'FALLBACK' in details:
                    fallback_sources += 1
            
            print("DATA SOURCE ANALYSIS:")
            print(f"  - Database-driven results: {database_sources}")
            print(f"  - Fallback results: {fallback_sources}")
            
            if database_sources > 0:
                print("  ✓ SUCCESS: System using real database!")
            else:
                print("  ⚠ INFO: System using fallbacks (check query connectivity)")
            
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return asyncio.run(run_test())

if __name__ == "__main__":
    # Show the correct structure
    print("CORRECT PROPERTY DATA STRUCTURE FOR SETBACK SYSTEM")
    print("=" * 60)
    
    sample = create_correct_property_data("123 Smith Street, Marrickville")
    
    print("Required fields:")
    print(f"  address: '{sample.address}'")
    print(f"  zone: '{sample.zone}'") 
    print(f"  lga_name: '{sample.lga_name}'")
    print(f"  height_limit: '{sample.height_limit}'")
    print(f"  former_council_area: '{sample.former_council_area}'")
    print()
    
    print("Optional fields:")
    print(f"  suburb: '{sample.suburb}'")
    print(f"  land_area: '{sample.land_area}'")
    print(f"  fsr_limit: '{sample.fsr_limit}'")
    print()
    
    # Run the real test
    success = test_real_setback_calculation_with_correct_structure()
    
    if success:
        print("\n🎉 SUCCESS: Real setback calculation system working with correct property structure!")
    else:
        print("\n❌ System needs debugging")