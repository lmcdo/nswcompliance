#!/usr/bin/env python3
"""
UI Swap Verification Script
Verifies that UI components were copied and connected to APIs
"""

import os
import json
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def verify_components_copied() -> dict:
    """Verify new UI components exist"""
    results = {}

    # Key components that should exist
    expected_components = [
        "components/header.tsx",
        "components/property-panel.tsx",
        "components/assessment-panel.tsx",
        "components/property-card.tsx",
        "components/ui/card.tsx",
        "components/ui/button.tsx",
        "components/ui/input.tsx"
    ]

    for component in expected_components:
        exists = os.path.exists(component)
        component_name = component.replace('/', '_').replace('.tsx', '')
        results[component_name] = exists

        if exists:
            print(f"✅ Component found: {component}")
        else:
            print(f"❌ Missing component: {component}")

    return results

def verify_api_connections() -> dict:
    """Verify components are connected to APIs"""
    results = {}

    # Check PropertyCard has API connection
    property_card = "components/property-card.tsx"
    if os.path.exists(property_card):
        with open(property_card, 'r') as f:
            content = f.read()

            has_fetch = 'fetch(' in content
            has_api_property = '/api/property' in content

            results['property_api_connected'] = has_fetch and has_api_property

            if has_fetch and has_api_property:
                print("✅ PropertyCard connected to /api/property")
            else:
                print("❌ PropertyCard not connected to API")
    else:
        results['property_api_connected'] = False
        print("❌ PropertyCard not found")

    # Check AssessmentPanel has compliance API
    assessment_panel = "components/assessment-panel.tsx"
    if os.path.exists(assessment_panel):
        with open(assessment_panel, 'r') as f:
            content = f.read()

            has_compliance_api = '/api/compliance' in content
            results['compliance_api_connected'] = has_compliance_api

            if has_compliance_api:
                print("✅ AssessmentPanel connected to compliance API")
            else:
                print("⚠️ AssessmentPanel may not have compliance API")
    else:
        results['compliance_api_connected'] = False

    return results

def verify_main_page_updated() -> dict:
    """Verify main page uses new UI"""
    results = {}

    main_page = "app/page.tsx"
    if os.path.exists(main_page):
        with open(main_page, 'r') as f:
            content = f.read()

            # Check for new UI imports
            has_new_imports = any(comp in content for comp in [
                'Header', 'PropertyPanel', 'AssessmentPanel'
            ])

            # Check it's not the old page
            is_new_ui = 'min-h-screen bg-white' in content and 'PropertyPanel' in content

            results['main_page_updated'] = has_new_imports and is_new_ui

            if is_new_ui:
                print("✅ Main page updated with new UI")
            else:
                print("❌ Main page not updated or still old UI")
    else:
        results['main_page_updated'] = False
        print("❌ Main page not found")

    return results

def verify_test_page() -> dict:
    """Verify test page was created"""
    test_page = "app/ui-test/page.tsx"
    exists = os.path.exists(test_page)

    if exists:
        print("✅ Test page created at /ui-test")
    else:
        print("⚠️ Test page not found")

    return {'test_page': exists}

def verify_typescript_compiles() -> dict:
    """Verify TypeScript compiles without errors"""
    print("\nChecking TypeScript compilation...")

    try:
        result = subprocess.run(
            ['npx', 'tsc', '--noEmit', '--skipLibCheck'],
            capture_output=True,
            text=True,
            timeout=30
        )

        success = result.returncode == 0

        if success:
            print("✅ TypeScript compilation successful")
        else:
            print("⚠️ TypeScript compilation warnings:")
            print(result.stderr[:500])  # Show first 500 chars

        return {'typescript_compiles': success}

    except subprocess.TimeoutExpired:
        print("⚠️ TypeScript check timed out")
        return {'typescript_compiles': False}
    except Exception as e:
        print(f"⚠️ TypeScript check failed: {e}")
        return {'typescript_compiles': False}

def verify_dependencies() -> dict:
    """Verify UI dependencies are installed"""
    results = {}

    if os.path.exists("package.json"):
        with open("package.json", 'r') as f:
            package_data = json.load(f)
            deps = {**package_data.get('dependencies', {}),
                   **package_data.get('devDependencies', {})}

            ui_deps = [
                'lucide-react',
                'clsx',
                'tailwindcss'
            ]

            for dep in ui_deps:
                installed = dep in deps
                results[f"dep_{dep.replace('-', '_')}"] = installed

                if installed:
                    print(f"✅ Dependency found: {dep}")
                else:
                    print(f"⚠️ Missing dependency: {dep}")

    return results

def verify_backup_created() -> dict:
    """Verify backup was created"""
    backup_dir = "migratePRPs/backup"
    exists = os.path.exists(backup_dir)

    if exists:
        # Check for recent backup
        backups = list(Path(backup_dir).glob("ui_swap_*"))
        if backups:
            latest = max(backups, key=os.path.getctime)
            print(f"✅ Backup found: {latest}")
            return {'backup_created': True}

    print("⚠️ No recent backup found")
    return {'backup_created': False}

def calculate_success_rate(results: dict) -> float:
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
    print("\n" + "="*50)
    print("UI SWAP VERIFICATION")
    print("="*50 + "\n")

    results = {
        'components': verify_components_copied(),
        'api_connections': verify_api_connections(),
        'main_page': verify_main_page_updated(),
        'test_page': verify_test_page(),
        'typescript': verify_typescript_compiles(),
        'dependencies': verify_dependencies(),
        'backup': verify_backup_created()
    }

    # Calculate success rate
    success_rate = calculate_success_rate(results)

    # Determine status
    if success_rate >= 90:
        status = "PASSED"
        print(f"\n✅ UI SWAP VERIFICATION PASSED ({success_rate:.1f}%)")
    elif success_rate >= 70:
        status = "PARTIAL"
        print(f"\n⚠️ PARTIAL SUCCESS ({success_rate:.1f}%)")
    else:
        status = "FAILED"
        print(f"\n❌ VERIFICATION FAILED ({success_rate:.1f}%)")

    # Save results
    output = {
        'verification': 'ui_swap',
        'timestamp': datetime.now().isoformat(),
        'success_rate': success_rate,
        'status': status,
        'detailed_results': results,
        'test_urls': [
            'http://localhost:3007',
            'http://localhost:3007/ui-test'
        ],
        'recommendations': []
    }

    # Add recommendations
    if success_rate < 100:
        if not results.get('backup', {}).get('backup_created'):
            output['recommendations'].append("Backup not found - migration may not have run")
        if not results.get('api_connections', {}).get('property_api_connected'):
            output['recommendations'].append("PropertyCard not connected to API")
        if success_rate < 90:
            output['recommendations'].append("Run: npm install to install missing dependencies")
            output['recommendations'].append("Check component imports and API connections")

    # Write results
    os.makedirs("migratePRPs/results", exist_ok=True)
    with open("migratePRPs/results/ui_swap_verification.json", 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: migratePRPs/results/ui_swap_verification.json")
    print("\n📋 Next steps:")
    print("1. Start dev server: npm run dev")
    print("2. Test main app: http://localhost:3007")
    print("3. Test new UI: http://localhost:3007/ui-test")

    # Exit code based on success
    sys.exit(0 if status == "PASSED" else 1)

if __name__ == "__main__":
    main()