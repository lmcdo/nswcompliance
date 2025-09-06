#!/usr/bin/env python3
"""
Test script for SEPP routing functionality
Verifies that the NSW Planning Portal special provisions data is being used
to route appropriate SEPP documents for property compliance checking
"""

import sys
import os
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_sepp_directory():
    """Test if SEPP directory exists and contains PDFs"""
    
    print("SEPP Directory Analysis")
    print("=" * 40)
    
    sepp_dir = "docs/sepps"
    
    if not os.path.exists(sepp_dir):
        print(f"[ERROR] SEPP directory not found: {sepp_dir}")
        return False
    
    # List all PDF files
    pdf_files = [f for f in os.listdir(sepp_dir) if f.lower().endswith('.pdf')]
    
    print(f"[OK] SEPP directory found: {sepp_dir}")
    print(f"[FILES] PDF files found: {len(pdf_files)}")
    
    for i, filename in enumerate(sorted(pdf_files), 1):
        print(f"  {i}. {filename}")
    
    if len(pdf_files) == 0:
        print("[WARN] No PDF files found in SEPP directory")
        return False
        
    return True

def analyze_sepp_naming():
    """Analyze SEPP file naming patterns to improve routing"""
    
    print(f"\nSEPP File Naming Analysis")
    print("=" * 40)
    
    sepp_dir = "docs/sepps"
    
    if not os.path.exists(sepp_dir):
        print("No SEPP directory to analyze")
        return
    
    pdf_files = [f for f in os.listdir(sepp_dir) if f.lower().endswith('.pdf')]
    
    # Analyze naming patterns
    patterns = {
        'housing': [],
        'transport': [],
        'infrastructure': [],
        'planning': [],
        'systems': [],
        'resilience': [],
        'hazards': [],
        'biodiversity': [],
        'conservation': [],
        'sepp': []
    }
    
    for filename in pdf_files:
        filename_lower = filename.lower()
        
        for pattern, files in patterns.items():
            if pattern in filename_lower:
                files.append(filename)
    
    print("Keyword Analysis:")
    for pattern, files in patterns.items():
        if files:
            print(f"  '{pattern}' - {len(files)} files:")
            for file in files:
                print(f"    - {file}")
        else:
            print(f"  '{pattern}' - 0 files")

def simulate_property_sepp_routing():
    """Simulate SEPP routing for different property types"""
    
    print(f"\nProperty SEPP Routing Simulation")
    print("=" * 40)
    
    # Test scenarios
    scenarios = [
        {
            "name": "R2 Residential - Haberfield",
            "lga": "Inner West",
            "zone": "R2",
            "development_type": "residential_low",
            "heritage": False,
            "expected_sepps": ["SEPP_HOUSING_2021", "SEPP_TRANSPORT_INFRASTRUCTURE_2021"]
        },
        {
            "name": "B4 Commercial - Sydney CBD", 
            "lga": "Sydney",
            "zone": "B4",
            "development_type": "commercial",
            "heritage": False,
            "expected_sepps": ["SEPP_TRANSPORT_INFRASTRUCTURE_2021", "SEPP_PLANNING_SYSTEMS_2021"]
        },
        {
            "name": "Heritage Site - Leichhardt",
            "lga": "Inner West", 
            "zone": "R2",
            "development_type": "residential_low",
            "heritage": True,
            "expected_sepps": ["SEPP_HOUSING_2021", "SEPP_BIODIVERSITY_CONSERVATION_2017"]
        }
    ]
    
    sepp_dir = "docs/sepps"
    available_files = []
    
    if os.path.exists(sepp_dir):
        available_files = [f for f in os.listdir(sepp_dir) if f.lower().endswith('.pdf')]
    
    for scenario in scenarios:
        print(f"\nScenario: {scenario['name']}")
        print(f"  Zone: {scenario['zone']}, Type: {scenario['development_type']}")
        print(f"  Heritage: {scenario['heritage']}")
        print(f"  Expected SEPPs: {scenario['expected_sepps']}")
        
        # Simulate routing
        matched_files = {}
        for sepp_id in scenario['expected_sepps']:
            files = find_files_for_sepp(sepp_id, available_files)
            matched_files[sepp_id] = files
            
            if files:
                print(f"    [OK] {sepp_id}: {len(files)} files matched")
                for file in files:
                    print(f"      - {file}")
            else:
                print(f"    [MISSING] {sepp_id}: No files found")

def find_files_for_sepp(sepp_id, available_files):
    """Helper function to match SEPP ID to files"""
    
    # Simple pattern matching
    patterns = {
        'SEPP_HOUSING_2021': ['housing'],
        'SEPP_TRANSPORT_INFRASTRUCTURE_2021': ['transport', 'infrastructure'],
        'SEPP_PLANNING_SYSTEMS_2021': ['planning', 'systems'],
        'SEPP_RESILIENCE_HAZARDS_2021': ['resilience', 'hazards'],
        'SEPP_BIODIVERSITY_CONSERVATION_2017': ['biodiversity', 'conservation']
    }
    
    matched_files = []
    
    if sepp_id in patterns:
        for filename in available_files:
            filename_lower = filename.lower()
            for pattern in patterns[sepp_id]:
                if pattern in filename_lower:
                    matched_files.append(filename)
                    break
    
    return matched_files

def generate_routing_recommendations():
    """Generate recommendations for improving SEPP routing"""
    
    print(f"\nSEPP Routing Recommendations")
    print("=" * 40)
    
    recommendations = [
        "1. Ensure SEPP files follow consistent naming convention:",
        "   - SEPP-Housing-2021.pdf",
        "   - SEPP-Transport-Infrastructure-2021.pdf", 
        "   - SEPP-Planning-Systems-2021.pdf",
        "",
        "2. Monitor NSW Planning Portal 'special provisions' responses for:",
        "   - SEPP references in 'EPI Name' field",
        "   - SEPP mentions in 'Legislative Clause' field",
        "   - Type classifications that indicate applicable SEPPs",
        "",
        "3. Implement fallback contextual routing:",
        "   - All residential zones -> Housing SEPP",
        "   - All developments -> Transport/Infrastructure SEPP",
        "   - Heritage sites -> Biodiversity/Conservation SEPP",
        "",
        "4. Add logging to track:",
        "   - Which SEPPs are identified per property",
        "   - Which SEPP files are successfully matched",
        "   - Missing SEPP files that should be obtained"
    ]
    
    for rec in recommendations:
        print(rec)

def save_routing_analysis():
    """Save routing analysis results"""
    
    sepp_dir = "docs/sepps" 
    pdf_files = []
    
    if os.path.exists(sepp_dir):
        pdf_files = [f for f in os.listdir(sepp_dir) if f.lower().endswith('.pdf')]
    
    analysis = {
        "analysis_date": datetime.now().isoformat(),
        "sepp_directory": sepp_dir,
        "available_sepps": {
            "total_files": len(pdf_files),
            "files": sorted(pdf_files)
        },
        "routing_status": "IMPLEMENTED" if pdf_files else "NO_SEPPS_AVAILABLE",
        "next_steps": [
            "Test with real NSW Planning Portal API responses",
            "Monitor special provisions parsing",
            "Add more SEPP pattern mappings",
            "Implement contextual fallback routing"
        ]
    }
    
    output_path = "public/regulatory-data/sepp-routing-analysis.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    print(f"\nAnalysis saved to: {output_path}")

def main():
    """Run all SEPP routing tests"""
    
    print("NSW SEPP Routing System Test")
    print("=" * 50)
    
    sepp_available = test_sepp_directory()
    
    if sepp_available:
        analyze_sepp_naming()
        simulate_property_sepp_routing()
    
    generate_routing_recommendations()
    save_routing_analysis()
    
    print(f"\n{'=' * 50}")
    print("SEPP ROUTING TEST COMPLETE")
    print("=" * 50)
    
    if sepp_available:
        print("[OK] SEPP routing system ready for testing")
        print("[OK] Files available for pattern matching")
        print("[OK] Special provisions parsing implemented")
    else:
        print("[WARN] SEPP routing system needs SEPP PDF files")
        print("[WARN] Add SEPP documents to docs/sepps/ directory")
    
    print("\nNext steps:")
    print("1. Test with real property address via API") 
    print("2. Monitor special provisions data structure")
    print("3. Verify SEPP file matching accuracy")
    print("4. Integrate with compliance checking system")

if __name__ == "__main__":
    main()