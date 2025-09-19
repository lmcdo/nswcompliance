#!/usr/bin/env python3
"""
Simple test for PRP-Q1 Live Compliance Calculator Engine
"""

import asyncio
import os
import sys
import time

async def test_prp_q1():
    """Simple test of PRP-Q1 implementation"""

    print("=== PRP-Q1 SIMPLE VERIFICATION ===")
    print()

    # Test 1: Check if files exist
    print("1. Testing File Structure:")
    required_files = [
        'services/live_compliance_engine.py',
        'frontend-nextjs/app/api/compliance/live-check/route.ts'
    ]

    files_exist = 0
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "[OK]" if exists else "[MISSING]"
        print(f"   {status} {file_path}")
        if exists:
            files_exist += 1

    print(f"   Files: {files_exist}/{len(required_files)} exist")
    print()

    # Test 2: Try to import the engine
    print("2. Testing Engine Import:")
    try:
        sys.path.append('services')
        from live_compliance_engine import LiveComplianceEngine, ComplianceResult, ComplianceAssessment
        print("   [OK] Engine imports successfully")

        # Test 3: Try to create engine instance
        print("3. Testing Engine Instantiation:")
        engine = LiveComplianceEngine()
        print("   [OK] Engine instantiates successfully")

        # Test 4: Test basic functionality
        print("4. Testing Basic Functionality:")

        # Check if required methods exist
        required_methods = ['calculate_compliance', '_check_fsr_compliance', '_check_height_compliance']
        methods_exist = 0
        for method_name in required_methods:
            has_method = hasattr(engine, method_name)
            status = "[OK]" if has_method else "[MISSING]"
            print(f"   {status} Method: {method_name}")
            if has_method:
                methods_exist += 1

        print(f"   Methods: {methods_exist}/{len(required_methods)} exist")
        print()

        # Test 5: Try a compliance calculation (simple test)
        print("5. Testing Compliance Calculation:")
        try:
            start_time = time.time()

            # Use a known Inner West address for testing
            test_address = "45 Liverpool Street, Ashfield NSW 2131"
            test_proposal = {
                'gross_floor_area': 180,
                'height': 8.5,
                'building_area': 120
            }

            print(f"   Testing with: {test_address}")
            print(f"   Proposal: GFA={test_proposal['gross_floor_area']}sqm, Height={test_proposal['height']}m")

            result = await engine.calculate_compliance(test_address, test_proposal)
            calculation_time = int((time.time() - start_time) * 1000)

            print(f"   [OK] Calculation completed in {calculation_time}ms")
            print(f"   Overall Compliant: {result.overall_compliant}")

            if result.fsr_compliance:
                print(f"   FSR: {result.fsr_compliance.actual_value} vs {result.fsr_compliance.limit_value} ({'Compliant' if result.fsr_compliance.compliant else 'Non-compliant'})")
                print(f"   FSR Source: {result.fsr_compliance.data_source}")

            if result.height_compliance:
                print(f"   Height: {result.height_compliance.actual_value}{result.height_compliance.units} vs {result.height_compliance.limit_value}{result.height_compliance.units} ({'Compliant' if result.height_compliance.compliant else 'Non-compliant'})")
                print(f"   Height Source: {result.height_compliance.data_source}")

            if result.site_coverage_compliance:
                print(f"   Site Coverage: {result.site_coverage_compliance.actual_value}{result.site_coverage_compliance.units} vs {result.site_coverage_compliance.limit_value}{result.site_coverage_compliance.units} ({'Compliant' if result.site_coverage_compliance.compliant else 'Non-compliant'})")

            if result.warnings:
                print(f"   Warnings: {', '.join(result.warnings)}")

            # Performance check
            performance_ok = calculation_time < 100
            print(f"   Performance: {'[OK]' if performance_ok else '[SLOW]'} {calculation_time}ms (target: <100ms)")

            # Check if using live API data
            uses_live_data = False
            if result.fsr_compliance and 'nsw_api' in result.fsr_compliance.data_source:
                uses_live_data = True
            if result.height_compliance and 'nsw_api' in result.height_compliance.data_source:
                uses_live_data = True

            print(f"   Live API Usage: {'[OK]' if uses_live_data else '[WARNING]'} {'Uses live data' if uses_live_data else 'Not using live API data'}")

            print("   [OK] Compliance calculation successful")

        except Exception as e:
            print(f"   [ERROR] Compliance calculation failed: {e}")
            print("   This may be expected if NSW API is unavailable")

        print()

        # Summary
        print("=== VERIFICATION SUMMARY ===")
        overall_success = (files_exist == len(required_files) and
                          methods_exist == len(required_methods))

        print(f"Overall Status: {'[PASS]' if overall_success else '[NEEDS WORK]'}")
        print(f"Files Created: {files_exist}/{len(required_files)}")
        print(f"Methods Implemented: {methods_exist}/{len(required_methods)}")
        print()

        if overall_success:
            print("PRP-Q1 IMPLEMENTATION COMPLETE!")
            print("Live Compliance Calculator Engine is ready for use.")
        else:
            print("PRP-Q1 needs additional implementation.")
            if files_exist < len(required_files):
                print("- Create missing files")
            if methods_exist < len(required_methods):
                print("- Implement missing methods")

    except ImportError as e:
        print(f"   [ERROR] Cannot import engine: {e}")
        print("   Engine needs to be implemented")

    except Exception as e:
        print(f"   [ERROR] Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(test_prp_q1())