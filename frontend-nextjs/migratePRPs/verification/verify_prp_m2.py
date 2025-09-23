#!/usr/bin/env python3
"""
PRP-M2 Verification: Google Autocomplete Integration
Verifies that Google autocomplete is properly integrated
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

def verify_google_dependencies() -> Dict[str, bool]:
    """Verify Google Maps dependencies are installed"""
    results = {}

    if os.path.exists("package.json"):
        with open("package.json", 'r') as f:
            package_data = json.load(f)
            deps = {**package_data.get('dependencies', {}),
                   **package_data.get('devDependencies', {})}

            required = [
                '@googlemaps/js-api-loader',
                '@types/google.maps'
            ]

            for dep in required:
                installed = dep in deps
                results[f"dep_{dep.replace('/', '_').replace('@', '')}"] = installed

                if installed:
                    print(f"✅ Google dependency installed: {dep}")
                else:
                    print(f"❌ Missing dependency: {dep}")

    return results

def verify_autocomplete_components() -> Dict[str, bool]:
    """Verify autocomplete components exist"""
    results = {}

    components = [
        "components/new-ui/autocomplete/google-autocomplete.tsx",
        "components/new-ui/core/property-card-enhanced.tsx"
    ]

    for component in components:
        exists = os.path.exists(component)
        component_name = os.path.basename(component)
        results[component_name] = exists

        if exists:
            # Check component content
            with open(component, 'r') as f:
                content = f.read()
                has_google_imports = '@googlemaps/js-api-loader' in content
                has_autocomplete_logic = 'Autocomplete' in content

                if has_google_imports and has_autocomplete_logic:
                    print(f"✅ Component ready: {component_name}")
                else:
                    print(f"⚠️ Component incomplete: {component_name}")
                    results[component_name] = False
        else:
            print(f"❌ Missing component: {component_name}")

    return results

def verify_env_configuration() -> Dict[str, bool]:
    """Verify environment configuration"""
    results = {}

    env_exists = os.path.exists(".env.local")
    results['env_file'] = env_exists

    if env_exists:
        with open(".env.local", 'r') as f:
            content = f.read()
            has_api_key = 'NEXT_PUBLIC_GOOGLE_MAPS_API_KEY' in content
            results['api_key_configured'] = has_api_key

            if has_api_key:
                print("✅ Google Maps API key configured")
            else:
                print("⚠️ Google Maps API key not configured in .env.local")
    else:
        print("⚠️ .env.local not found")
        results['api_key_configured'] = False

    return results

def verify_test_pages() -> Dict[str, bool]:
    """Verify test pages were created"""
    results = {}

    test_pages = [
        "app/autocomplete-test/page.tsx",
        "app/new-ui-test/page.tsx"
    ]

    for page in test_pages:
        exists = os.path.exists(page)
        page_name = page.split('/')[1]
        results[f"test_{page_name}"] = exists

        if exists:
            print(f"✅ Test page ready: /{page_name}")
        else:
            print(f"⚠️ Test page not found: {page}")

    return results

def calculate_success_rate(results: Dict[str, Any]) -> float:
    """Calculate overall success rate"""
    all_checks = []

    for category_results in results.values():
        if isinstance(category_results, dict):
            all_checks.extend(category_results.values())

    if not all_checks:
        return 0.0

    passed = sum(1 for check in all_checks if check is True)
    return (passed / len(all_checks)) * 100

def main():
    print("\n" + "="*60)
    print("PRP-M2 VERIFICATION: Google Autocomplete Integration")
    print("="*60 + "\n")

    results = {
        'dependencies': verify_google_dependencies(),
        'components': verify_autocomplete_components(),
        'environment': verify_env_configuration(),
        'test_pages': verify_test_pages()
    }

    # Calculate success rate
    success_rate = calculate_success_rate(results)

    # Determine status
    if success_rate >= 90:
        status = "PASSED"
        print(f"\n✅ VERIFICATION PASSED ({success_rate:.1f}%)")
    elif success_rate >= 70:
        status = "PARTIAL"
        print(f"\n⚠️ PARTIAL SUCCESS ({success_rate:.1f}%)")
    else:
        status = "FAILED"
        print(f"\n❌ VERIFICATION FAILED ({success_rate:.1f}%)")

    # Save results
    output = {
        'prp': 'M2',
        'timestamp': datetime.now().isoformat(),
        'success_rate': success_rate,
        'status': status,
        'detailed_results': results,
        'recommendations': []
    }

    # Add recommendations
    if not results.get('environment', {}).get('api_key_configured'):
        output['recommendations'].append("Add NEXT_PUBLIC_GOOGLE_MAPS_API_KEY to .env.local")
    if success_rate < 90:
        output['recommendations'].append("Install missing dependencies: npm install")
        output['recommendations'].append("Test autocomplete at /autocomplete-test")

    # Write results
    os.makedirs("migratePRPs/results", exist_ok=True)
    with open("migratePRPs/results/verify_m2_results.json", 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: migratePRPs/results/verify_m2_results.json")

    # Exit code based on success
    sys.exit(0 if status == "PASSED" else 1)

if __name__ == "__main__":
    main()