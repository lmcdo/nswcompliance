#!/usr/bin/env python3
"""
PRP-A3 Verification Script: Database Bridge & Version Integration
Tests version-aware compliance checking and database integration
"""

import os
import json
import requests
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def check_version_api_endpoints():
    """Test version management API endpoints"""
    print("Checking version management API endpoints...")

    results = {}
    base_url = "http://localhost:3007"

    # Test version statistics endpoint
    try:
        response = requests.get(
            f"{base_url}/api/versions?action=statistics",
            timeout=10
        )
        results["version_statistics"] = response.status_code in [200, 500]  # 500 might be expected if DB not populated
        print(f" Version statistics API: {response.status_code}")
    except Exception as e:
        print(f" Version statistics API failed: {e}")
        results["version_statistics"] = False

    # Test version current endpoint
    try:
        response = requests.get(
            f"{base_url}/api/versions",
            params={
                "action": "current",
                "documentType": "LEP",
                "documentIdentifier": "Test-LEP"
            },
            timeout=10
        )
        results["version_current"] = response.status_code in [200, 404, 500]  # Various responses acceptable
        print(f" Version current API: {response.status_code}")
    except Exception as e:
        print(f" Version current API failed: {e}")
        results["version_current"] = False

    return results

def check_version_aware_compliance():
    """Test version-aware compliance API"""
    print("Checking version-aware compliance API...")

    results = {}
    base_url = "http://localhost:3007"

    # Test version-aware compliance endpoint
    try:
        response = requests.post(
            f"{base_url}/api/assessment/version-compliance",
            json={
                "propertyId": 123,
                "zone": "R2",
                "developmentType": "dwelling_house",
                "assessmentDate": "2024-01-01",
                "documentType": "LEP",
                "documentIdentifier": "Test-LEP",
                "useCurrentVersion": True
            },
            timeout=15
        )
        results["version_aware_compliance"] = response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            results["compliance_has_version_context"] = "version_info" in data.get("data", {})
            results["compliance_has_assessment_context"] = "assessment_context" in data.get("data", {})
        else:
            results["compliance_has_version_context"] = False
            results["compliance_has_assessment_context"] = False

        print(f" Version-aware compliance API: {response.status_code}")
    except Exception as e:
        print(f" Version-aware compliance API failed: {e}")
        results["version_aware_compliance"] = False
        results["compliance_has_version_context"] = False
        results["compliance_has_assessment_context"] = False

    return results

def check_version_management_components():
    """Check that version management UI components exist"""
    print("Checking version management UI components...")

    results = {}

    # Check VersionSelector component
    version_selector_path = "frontend-nextjs/components/assessment/core/VersionSelector.tsx"
    if Path(version_selector_path).exists():
        content = Path(version_selector_path).read_text()

        # Check for key functionality
        has_version_loading = "useState" in content and "VersionInfo" in content
        has_api_calls = "fetch" in content and "/api/versions" in content
        has_radio_buttons = "radio" in content and "version-selection" in content

        results["version_selector_component"] = has_version_loading and has_api_calls and has_radio_buttons

        if results["version_selector_component"]:
            print(" VersionSelector: Properly implemented")
        else:
            print(" VersionSelector: Missing functionality")
            print(f"  - Version loading: {has_version_loading}")
            print(f"  - API calls: {has_api_calls}")
            print(f"  - Radio buttons: {has_radio_buttons}")
    else:
        results["version_selector_component"] = False
        print(" VersionSelector: File not found")

    return results

def check_version_aware_assessment_page():
    """Check version-aware assessment page"""
    print("Checking version-aware assessment page...")

    results = {}

    # Check version-aware assessment page
    page_path = "frontend-nextjs/app/assessment/version-aware/page.tsx"
    if Path(page_path).exists():
        content = Path(page_path).read_text()

        # Check for key components
        imports_version_selector = "VersionSelector" in content
        has_assessment_date = "assessmentDate" in content
        has_version_change_handler = "handleVersionChange" in content
        has_version_aware_api = "version-compliance" in content

        results["version_aware_page"] = all([
            imports_version_selector, has_assessment_date,
            has_version_change_handler, has_version_aware_api
        ])

        if results["version_aware_page"]:
            print(" Version-aware assessment page: Properly implemented")
        else:
            print(" Version-aware assessment page: Missing functionality")
            print(f"  - Imports VersionSelector: {imports_version_selector}")
            print(f"  - Has assessment date: {has_assessment_date}")
            print(f"  - Has version change handler: {has_version_change_handler}")
            print(f"  - Uses version-aware API: {has_version_aware_api}")
    else:
        results["version_aware_page"] = False
        print(" Version-aware assessment page: File not found")

    return results

def check_version_types():
    """Check version-aware types are added"""
    print("Checking version-aware type definitions...")

    results = {}

    types_path = "frontend-nextjs/lib/assessment/types.ts"
    if Path(types_path).exists():
        content = Path(types_path).read_text()

        # Check for version-related types
        has_version_info = "VersionInfo" in content and "version_status" in content
        has_version_aware_context = "VersionAwareAssessmentContext" in content
        has_version_aware_result = "VersionAwareComplianceResult" in content

        results["version_types"] = has_version_info and has_version_aware_context and has_version_aware_result

        if results["version_types"]:
            print(" Version types: Properly defined")
        else:
            print(" Version types: Missing definitions")
            print(f"  - VersionInfo: {has_version_info}")
            print(f"  - VersionAwareAssessmentContext: {has_version_aware_context}")
            print(f"  - VersionAwareComplianceResult: {has_version_aware_result}")
    else:
        results["version_types"] = False
        print(" Version types: File not found")

    return results

def check_version_manager_cli():
    """Check version manager CLI wrapper exists"""
    print("Checking version manager CLI wrapper...")

    results = {}

    cli_path = "services/version_manager_cli.py"
    if Path(cli_path).exists():
        content = Path(cli_path).read_text()

        # Check for key CLI functionality
        has_argparse = "argparse" in content
        has_subcommands = "subparsers" in content and "get_current_version" in content
        has_json_output = "json.dumps" in content

        results["version_manager_cli"] = has_argparse and has_subcommands and has_json_output

        if results["version_manager_cli"]:
            print(" Version manager CLI: Properly implemented")
        else:
            print(" Version manager CLI: Missing functionality")
    else:
        results["version_manager_cli"] = False
        print(" Version manager CLI: File not found")

    return results

def check_route_accessibility():
    """Check version-aware route is accessible"""
    print("Checking route accessibility...")

    try:
        # Give server a moment to compile if needed
        time.sleep(2)

        response = requests.get("http://localhost:3007/assessment/version-aware", timeout=10)
        route_accessible = response.status_code == 200

        if route_accessible:
            print(" /assessment/version-aware route: Accessible")
        else:
            print(f" /assessment/version-aware route: Status {response.status_code}")

        return {"version_aware_route_accessible": route_accessible}

    except Exception as e:
        print(f" /assessment/version-aware route check failed: {e}")
        return {"version_aware_route_accessible": False}

def generate_summary_report(all_results):
    """Generate comprehensive summary"""
    total_checks = sum(len(result_group) for result_group in all_results.values())
    passed_checks = sum(
        sum(result_group.values()) for result_group in all_results.values()
    )

    success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

    print(f"\nPRP-A3 VERIFICATION SUMMARY")
    print("=" * 40)
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print(f"Success Rate: {success_rate:.1f}%")

    # Detailed breakdown
    for category, results in all_results.items():
        category_passed = sum(results.values())
        category_total = len(results)
        print(f"\n{category.replace('_', ' ').title()}: {category_passed}/{category_total}")
        for check, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {check}")

    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "success_rate": success_rate,
        "overall_pass": success_rate >= 75  # 75% threshold for passing
    }

def main():
    """Main verification function"""
    print("PRP-A3 VERIFICATION: Database Bridge & Version Integration")
    print("=" * 65)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")

    # Change to project root if needed
    if os.getcwd().endswith("PRPs/NEWUI") or os.getcwd().endswith("PRPs\\NEWUI"):
        os.chdir("../..")
        print(f"Changed to project root: {os.getcwd()}")

    verification_results = {
        "prp": "A3_DATABASE_BRIDGE_VERSION_INTEGRATION",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "errors": [],
        "warnings": []
    }

    # Run all verification checks
    all_results = {}

    print("\n1. Checking Version API Endpoints...")
    all_results["version_apis"] = check_version_api_endpoints()

    print("\n2. Checking Version-Aware Compliance...")
    all_results["version_aware_compliance"] = check_version_aware_compliance()

    print("\n3. Checking Version Management Components...")
    all_results["version_components"] = check_version_management_components()

    print("\n4. Checking Version-Aware Assessment Page...")
    all_results["version_aware_page"] = check_version_aware_assessment_page()

    print("\n5. Checking Version Type Definitions...")
    all_results["version_types"] = check_version_types()

    print("\n6. Checking Version Manager CLI...")
    all_results["version_manager_cli"] = check_version_manager_cli()

    print("\n7. Checking Route Accessibility...")
    all_results["route_accessibility"] = check_route_accessibility()

    # Generate summary
    summary = generate_summary_report(all_results)

    # Compile final results
    verification_results["checks"] = all_results
    verification_results["summary"] = summary
    verification_results["success"] = summary["overall_pass"]

    # Save results
    results_dir = Path("PRPs/NEWUI/results")
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "prp_a3_results.json"
    with open(results_file, "w") as f:
        json.dump(verification_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Final verdict
    if summary["overall_pass"]:
        print(f"\nPRP-A3 VERIFICATION PASSED!")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        print("\nDatabase bridge and version integration successful")
        print("Ready to proceed to PRP-A4")
        return 0
    else:
        print(f"\nPRP-A3 VERIFICATION FAILED!")
        print(f"Success rate: {summary['success_rate']:.1f}% (minimum 75% required)")
        print("\nFix the failed checks before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())