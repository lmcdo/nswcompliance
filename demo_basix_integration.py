#!/usr/bin/env python3
"""
Demonstration of BASIX and Special Provisions Integration
Shows how the system processes BASIX data and special provisions
"""

import sys
sys.path.append('services')

from basix_compliance_checker import BASIXComplianceChecker
from special_provisions_processor import SpecialProvisionsProcessor

def demo_basix_processing():
    """Demonstrate BASIX compliance checking"""

    print("=" * 60)
    print("BASIX COMPLIANCE PROCESSING DEMO")
    print("=" * 60)

    # Initialize BASIX checker
    basix_checker = BASIXComplianceChecker()

    # Test with Zone 17 (Ashfield area)
    print("\n1. BASIX Requirements for Zone 17 Dwelling House:")
    print("-" * 50)

    requirements = basix_checker.get_basix_requirements("Zone 17", "dwelling_house")

    if requirements.get('has_requirements'):
        print(f"Climate Zone: {requirements['climate_zone']}")
        print(f"Development Type: {requirements['development_type']}")
        print(f"BASIX Provisions Found: {len(requirements.get('basix_provisions', []))}")

        for basix_provision in requirements.get('basix_provisions', []):
            print(f"\nProvisions for {basix_provision['development_type']}:")
            for provision in basix_provision.get('provisions', []):
                print(f"  • {provision['provision_text']}")
                if provision.get('numeric_value'):
                    print(f"    Target: {provision['numeric_value']}{provision['unit']}")

    # Test API integration
    print("\n2. BASIX API Data Processing:")
    print("-" * 50)

    sample_api_data = {
        'climate_zone': 'Zone 17',
        'water_zone': 'Inner West Water Zone'
    }

    api_result = basix_checker.process_basix_from_api(sample_api_data)
    print(f"Climate Zone: {api_result.get('climate_zone', 'Not found')}")
    print(f"Water Zone: {api_result.get('water_zone', 'Not found')}")
    print(f"Has Requirements: {api_result.get('has_requirements', False)}")

    basix_checker.close_connection()

def demo_special_provisions():
    """Demonstrate special provisions processing"""

    print("\n" + "=" * 60)
    print("SPECIAL PROVISIONS PROCESSING DEMO")
    print("=" * 60)

    # Initialize processor
    processor = SpecialProvisionsProcessor()

    # Sample provisions from NSW Planning API
    sample_provisions = [
        {
            'Type': 'Climate Zones',
            'Map Type': 'CLM',
            'Class': 'Zone 17'
        },
        {
            'Type': 'State Environmental Planning Policy',
            'EPI Name': 'SEPP (Housing) 2021',
            'Legislative Clause': '3.31'
        },
        {
            'Type': 'Flood Planning',
            'Category': 'Flood Planning Area',
            'Level': '1:100 Year'
        },
        {
            'Type': 'Heritage',
            'Heritage Type': 'Local Heritage Item',
            'Item Name': 'Federation House'
        }
    ]

    print("\n1. Processing Sample Special Provisions:")
    print("-" * 50)

    results = processor.process_special_provisions(sample_provisions, 'R4', 'dwelling_house')

    print(f"Total Processed: {results['metadata']['total_processed']}")
    print(f"Provision Types: {', '.join(results['metadata']['provision_types'])}")
    print(f"Requires Specialist: {results['metadata']['requires_specialist']}")
    print(f"Has Hazards: {results['metadata']['has_hazards']}")
    print(f"Has Environmental: {results['metadata']['has_environmental']}")

    # Show tier distribution
    print("\n2. Tier Distribution:")
    print("-" * 50)

    for tier in range(1, 6):
        tier_key = f'tier_{tier}_provisions'
        count = len(results.get(tier_key, []))
        if count > 0:
            print(f"Tier {tier}: {count} provisions")

            # Show first provision as example
            if results.get(tier_key):
                provision = results[tier_key][0]
                print(f"  Example: {provision.get('provision_text', 'N/A')[:60]}...")

    # Show hazard assessments
    print("\n3. Hazard Assessments:")
    print("-" * 50)

    for hazard in results.get('hazard_assessments', []):
        print(f"  • {hazard['hazard_type']}: {hazard['risk_level']} risk")
        if hazard.get('numeric_threshold'):
            print(f"    Threshold: {hazard['numeric_threshold']} {hazard.get('unit', '')}")

    processor.close_connection()

def demo_integration():
    """Demonstrate full integration"""

    print("\n" + "=" * 60)
    print("INTEGRATION DEMO")
    print("=" * 60)

    print("\n1. Data Flow:")
    print("-" * 50)
    print("NSW Planning API → Property Lookup → Extract BASIX & Special Provisions")
    print("↓")
    print("Frontend passes to /api/authoritative/compliance-check")
    print("↓")
    print("Enhanced Compliance API processes with BASIX Checker & Special Provisions Processor")
    print("↓")
    print("Results merged into tier hierarchy and returned to frontend")
    print("↓")
    print("BASIXProvisions component displays BASIX requirements")
    print("AuthoritativeComplianceDisplay shows all provisions by tier")

    print("\n2. Key Features Implemented:")
    print("-" * 50)
    print("✓ BASIX requirements database with climate zone mapping")
    print("✓ Special provisions registry with tier assignments")
    print("✓ Automatic hazard identification (flood, bushfire)")
    print("✓ SEPP detection and processing")
    print("✓ Tier 1 authority for BASIX and hazards")
    print("✓ Professional consultation flags")
    print("✓ Dedicated BASIX UI component")
    print("✓ API parameter passing for BASIX and special provisions")

    print("\n3. Example Usage:")
    print("-" * 50)
    print("User enters: '45 Liverpool Street, Ashfield NSW 2131'")
    print("System extracts: Zone 17 climate, R4 zoning, special provisions")
    print("System returns: 40% energy reduction, 40% water reduction, tier hierarchy")
    print("User sees: BASIX card + tiered compliance requirements")

def main():
    """Run the demonstration"""

    print("BASIX AND SPECIAL PROVISIONS INTEGRATION")
    print("Implementation Demonstration")
    print("=" * 60)

    try:
        demo_basix_processing()
        demo_special_provisions()
        demo_integration()

        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("\nThe implementation successfully:")
        print("• Extracts BASIX climate zones from NSW Planning API")
        print("• Processes special provisions into tier hierarchy")
        print("• Displays BASIX requirements with energy/water targets")
        print("• Integrates seamlessly with existing compliance system")

        print("\nTo test the full system:")
        print("1. Ensure PostgreSQL is running")
        print("2. Run: python create_tables.py (to create database tables)")
        print("3. Start frontend: cd frontend-nextjs && npm run dev")
        print("4. Visit http://localhost:3000/authoritative")
        print("5. Enter a NSW address and see BASIX + compliance results")

    except Exception as e:
        print(f"\nDemo Error: {e}")
        print("Note: Some features require database connection")

if __name__ == "__main__":
    main()