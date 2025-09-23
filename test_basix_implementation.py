#!/usr/bin/env python3
"""
Simple test to verify BASIX implementation components
"""

import os
import json

def test_files_created():
 """Test that all required files were created"""

 print("BASIX & Special Provisions Implementation Test")
 print("=" * 50)

 files_to_check = [
 # Database scripts
 ("scripts/create_basix_tables.sql", "Database schema"),

 # Backend services
 ("services/basix_compliance_checker.py", "BASIX compliance checker"),
 ("services/special_provisions_processor.py", "Special provisions processor"),

 # Frontend components
 ("frontend-nextjs/components/compliance/BASIXProvisions.tsx", "BASIX display component"),

 # API updates
 ("frontend-nextjs/app/api/authoritative/compliance-check/route.ts", "API route"),
 ("services/enhanced_compliance_api.py", "Enhanced compliance API"),
 ]

 created_count = 0
 total_count = len(files_to_check)

 for file_path, description in files_to_check:
 if os.path.exists(file_path):
 status = "CREATED"
 created_count += 1
 else:
 status = "MISSING"

 print(f" {status}: {description}")
 print(f" File: {file_path}")

 print(f"\nSummary: {created_count}/{total_count} files created")

 return created_count == total_count

def test_content_integration():
 """Test that content has been integrated"""

 print("\nContent Integration Test")
 print("=" * 30)

 # Check API route has BASIX parameters
 api_route_path = "frontend-nextjs/app/api/authoritative/compliance-check/route.ts"
 if os.path.exists(api_route_path):
 with open(api_route_path, 'r') as f:
 content = f.read()

 has_basix = 'basix_provisions' in content
 has_special = 'special_provisions' in content

 print(f" API Route BASIX support: {'YES' if has_basix else 'NO'}")
 print(f" API Route Special provisions support: {'YES' if has_special else 'NO'}")

 return has_basix and has_special

 return False

def test_component_features():
 """Test component features"""

 print("\nComponent Features Test")
 print("=" * 25)

 # Check BASIX component features
 basix_component_path = "frontend-nextjs/components/compliance/BASIXProvisions.tsx"
 if os.path.exists(basix_component_path):
 with open(basix_component_path, 'r') as f:
 content = f.read()

 features = {
 'Climate Zone Display': 'climateZone' in content,
 'Water Zone Display': 'waterZone' in content,
 'Numeric Values': 'numeric_value' in content,
 'Energy Icon': 'Zap' in content,
 'Water Icon': 'Droplets' in content,
 'BASIX Portal Link': 'basix.nsw.gov.au' in content
 }

 for feature, present in features.items():
 print(f" {feature}: {'YES' if present else 'NO'}")

 return all(features.values())

 return False

def main():
 """Run all tests"""

 print("Testing BASIX and Special Provisions Implementation")
 print("=" * 60)

 # Test file creation
 files_ok = test_files_created()

 # Test content integration
 content_ok = test_content_integration()

 # Test component features
 features_ok = test_component_features()

 # Overall result
 print("\n" + "=" * 60)
 print("OVERALL RESULT")
 print("=" * 60)

 print(f"Files Created: {'PASS' if files_ok else 'FAIL'}")
 print(f"Content Integration: {'PASS' if content_ok else 'FAIL'}")
 print(f"Component Features: {'PASS' if features_ok else 'FAIL'}")

 overall_success = files_ok and content_ok and features_ok

 print(f"\nImplementation Status: {'COMPLETE' if overall_success else 'PARTIAL'}")

 if overall_success:
 print("\nNext Steps:")
 print("1. Start the frontend development server")
 print("2. Test with a real NSW address")
 print("3. Verify BASIX data appears in compliance results")
 else:
 print("\nIssues to fix:")
 if not files_ok:
 print("- Some files were not created")
 if not content_ok:
 print("- API integration incomplete")
 if not features_ok:
 print("- Component features missing")

 return overall_success

if __name__ == "__main__":
 success = main()
 exit(0 if success else 1)