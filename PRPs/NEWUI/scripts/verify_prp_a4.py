#!/usr/bin/env python3
"""
PRP-A4 Verification Script: UI Data Binding
Tests real-time data flow, loading states, and form validation
"""

import os
import json
import requests
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def check_assessment_state_hook():
    """Check useAssessment hook implementation"""
    print("Checking assessment state management hook...")

    results = {}

    hook_path = "frontend-nextjs/hooks/assessment/useAssessment.ts"
    if Path(hook_path).exists():
        content = Path(hook_path).read_text()

        # Check for comprehensive state management
        has_state_interface = "AssessmentState" in content and "AssessmentActions" in content
        has_form_validation = "validateForm" in content and "formValid" in content
        has_loading_states = "Loading" in content and "Error" in content
        has_real_time_updates = "useCallback" in content and "useEffect" in content

        results["assessment_state_hook"] = all([
            has_state_interface, has_form_validation,
            has_loading_states, has_real_time_updates
        ])

        if results["assessment_state_hook"]:
            print(" Assessment state hook: Properly implemented")
        else:
            print(" Assessment state hook: Missing functionality")
            print(f"  - State interface: {has_state_interface}")
            print(f"  - Form validation: {has_form_validation}")
            print(f"  - Loading states: {has_loading_states}")
            print(f"  - Real-time updates: {has_real_time_updates}")
    else:
        results["assessment_state_hook"] = False
        print(" Assessment state hook: File not found")

    return results

def check_loading_states_components():
    """Check loading states and error handling components"""
    print("Checking loading states and error handling components...")

    results = {}

    loading_states_path = "frontend-nextjs/components/assessment/core/LoadingStates.tsx"
    if Path(loading_states_path).exists():
        content = Path(loading_states_path).read_text()

        # Check for comprehensive loading components
        has_loading_spinner = "LoadingSpinner" in content
        has_property_loading = "PropertyLoading" in content
        has_compliance_loading = "ComplianceLoading" in content
        has_error_display = "ErrorDisplay" in content
        has_validation_errors = "ValidationErrors" in content

        results["loading_states_components"] = all([
            has_loading_spinner, has_property_loading,
            has_compliance_loading, has_error_display, has_validation_errors
        ])

        if results["loading_states_components"]:
            print(" Loading states components: Properly implemented")
        else:
            print(" Loading states components: Missing functionality")
            print(f"  - Loading spinner: {has_loading_spinner}")
            print(f"  - Property loading: {has_property_loading}")
            print(f"  - Compliance loading: {has_compliance_loading}")
            print(f"  - Error display: {has_error_display}")
            print(f"  - Validation errors: {has_validation_errors}")
    else:
        results["loading_states_components"] = False
        print(" Loading states components: File not found")

    return results

def check_validated_form_components():
    """Check form validation components"""
    print("Checking form validation components...")

    results = {}

    validated_form_path = "frontend-nextjs/components/assessment/core/ValidatedForm.tsx"
    if Path(validated_form_path).exists():
        content = Path(validated_form_path).read_text()

        # Check for validated form components
        has_address_input = "ValidatedAddressInput" in content
        has_development_selector = "ValidatedDevelopmentSelector" in content
        has_date_input = "ValidatedDateInput" in content
        has_submit_button = "AssessmentSubmitButton" in content
        has_error_handling = "error" in content.lower() and "validation" in content.lower()

        results["validated_form_components"] = all([
            has_address_input, has_development_selector,
            has_date_input, has_submit_button, has_error_handling
        ])

        if results["validated_form_components"]:
            print(" Validated form components: Properly implemented")
        else:
            print(" Validated form components: Missing functionality")
            print(f"  - Address input: {has_address_input}")
            print(f"  - Development selector: {has_development_selector}")
            print(f"  - Date input: {has_date_input}")
            print(f"  - Submit button: {has_submit_button}")
            print(f"  - Error handling: {has_error_handling}")
    else:
        results["validated_form_components"] = False
        print(" Validated form components: File not found")

    return results

def check_enhanced_assessment_page():
    """Check enhanced assessment page with data binding"""
    print("Checking enhanced assessment page...")

    results = {}

    page_path = "frontend-nextjs/app/assessment/enhanced/page.tsx"
    if Path(page_path).exists():
        content = Path(page_path).read_text()

        # Check for comprehensive data binding
        uses_assessment_hook = "useAssessment" in content
        has_real_time_validation = "ValidationErrors" in content
        has_loading_states = "PropertyLoading" in content and "ComplianceLoading" in content
        has_error_handling = "ErrorDisplay" in content
        has_form_components = "ValidatedAddressInput" in content and "ValidatedDevelopmentSelector" in content

        results["enhanced_assessment_page"] = all([
            uses_assessment_hook, has_real_time_validation,
            has_loading_states, has_error_handling, has_form_components
        ])

        if results["enhanced_assessment_page"]:
            print(" Enhanced assessment page: Properly implemented")
        else:
            print(" Enhanced assessment page: Missing functionality")
            print(f"  - Uses assessment hook: {uses_assessment_hook}")
            print(f"  - Real-time validation: {has_real_time_validation}")
            print(f"  - Loading states: {has_loading_states}")
            print(f"  - Error handling: {has_error_handling}")
            print(f"  - Form components: {has_form_components}")
    else:
        results["enhanced_assessment_page"] = False
        print(" Enhanced assessment page: File not found")

    return results

def check_route_accessibility():
    """Check enhanced route is accessible"""
    print("Checking route accessibility...")

    try:
        # Give server a moment to compile if needed
        time.sleep(2)

        response = requests.get("http://localhost:3007/assessment/enhanced", timeout=10)
        route_accessible = response.status_code == 200

        if route_accessible:
            print(" /assessment/enhanced route: Accessible")
        else:
            print(f" /assessment/enhanced route: Status {response.status_code}")

        return {"enhanced_route_accessible": route_accessible}

    except Exception as e:
        print(f" /assessment/enhanced route check failed: {e}")
        return {"enhanced_route_accessible": False}

def check_typescript_compilation():
    """Check TypeScript compilation with new components"""
    print("Checking TypeScript compilation...")

    try:
        os.chdir("frontend-nextjs")

        # Run type check
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            capture_output=True,
            text=True,
            timeout=60
        )

        os.chdir("..")

        type_check_passed = result.returncode == 0

        if type_check_passed:
            print(" TypeScript compilation: No errors")
        else:
            print(" TypeScript compilation: Errors found")
            if result.stderr:
                print("STDERR:", result.stderr[-500:])  # Last 500 chars

        return {"typescript_compilation": type_check_passed}

    except Exception as e:
        os.chdir("..")
        print(f" TypeScript compilation failed: {e}")
        return {"typescript_compilation": False}

def check_data_binding_functionality():
    """Test real-time data binding through API calls"""
    print("Checking data binding functionality...")

    results = {}
    base_url = "http://localhost:3007"

    # Test enhanced assessment API with form data simulation
    try:
        # Simulate a complete assessment workflow
        response = requests.post(
            f"{base_url}/api/assessment",
            json={
                "action": "getCompliance",
                "propertyId": 456,
                "zone": "R3",
                "developmentType": "multi_dwelling_housing",
                "assessmentDate": "2024-06-15"
            },
            timeout=15
        )

        results["data_binding_api"] = response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            results["api_returns_structured_data"] = "compliance_items" in data.get("data", {})
            results["api_has_summary"] = "summary" in data.get("data", {})
        else:
            results["api_returns_structured_data"] = False
            results["api_has_summary"] = False

        print(f" Data binding API test: {response.status_code}")
    except Exception as e:
        print(f" Data binding API test failed: {e}")
        results["data_binding_api"] = False
        results["api_returns_structured_data"] = False
        results["api_has_summary"] = False

    return results

def generate_summary_report(all_results):
    """Generate comprehensive summary"""
    total_checks = sum(len(result_group) for result_group in all_results.values())
    passed_checks = sum(
        sum(result_group.values()) for result_group in all_results.values()
    )

    success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

    print(f"\nPRP-A4 VERIFICATION SUMMARY")
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
        "overall_pass": success_rate >= 80  # 80% threshold for passing
    }

def main():
    """Main verification function"""
    print("PRP-A4 VERIFICATION: UI Data Binding")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")

    # Change to project root if needed
    if os.getcwd().endswith("PRPs/NEWUI") or os.getcwd().endswith("PRPs\\NEWUI"):
        os.chdir("../..")
        print(f"Changed to project root: {os.getcwd()}")

    verification_results = {
        "prp": "A4_UI_DATA_BINDING",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "errors": [],
        "warnings": []
    }

    # Run all verification checks
    all_results = {}

    print("\n1. Checking Assessment State Hook...")
    all_results["assessment_state"] = check_assessment_state_hook()

    print("\n2. Checking Loading States Components...")
    all_results["loading_states"] = check_loading_states_components()

    print("\n3. Checking Validated Form Components...")
    all_results["validated_forms"] = check_validated_form_components()

    print("\n4. Checking Enhanced Assessment Page...")
    all_results["enhanced_page"] = check_enhanced_assessment_page()

    print("\n5. Checking Route Accessibility...")
    all_results["route_accessibility"] = check_route_accessibility()

    print("\n6. Checking TypeScript Compilation...")
    all_results["typescript"] = check_typescript_compilation()

    print("\n7. Checking Data Binding Functionality...")
    all_results["data_binding"] = check_data_binding_functionality()

    # Generate summary
    summary = generate_summary_report(all_results)

    # Compile final results
    verification_results["checks"] = all_results
    verification_results["summary"] = summary
    verification_results["success"] = summary["overall_pass"]

    # Save results
    results_dir = Path("PRPs/NEWUI/results")
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "prp_a4_results.json"
    with open(results_file, "w") as f:
        json.dump(verification_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    # Final verdict
    if summary["overall_pass"]:
        print(f"\nPRP-A4 VERIFICATION PASSED!")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        print("\nUI data binding with real-time validation successful")
        print("Ready to proceed to PRP-A5")
        return 0
    else:
        print(f"\nPRP-A4 VERIFICATION FAILED!")
        print(f"Success rate: {summary['success_rate']:.1f}% (minimum 80% required)")
        print("\nFix the failed checks before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())