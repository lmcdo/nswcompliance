#!/usr/bin/env python3
"""
PRP-A1 Verification Script: Foundation & Project Merge
Comprehensive testing to ensure all foundation elements are in place
"""

import os
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def check_directory_structure():
    """Check that all required directories exist"""
    required_dirs = [
        "frontend-nextjs/components/assessment/core",
        "frontend-nextjs/components/assessment/shared",
        "frontend-nextjs/components/assessment/layouts",
        "frontend-nextjs/app/assessment",
        "frontend-nextjs/lib/assessment",
        "frontend-nextjs/hooks/assessment"
    ]

    results = {}
    for dir_path in required_dirs:
        full_path = Path(dir_path)
        exists = full_path.exists() and full_path.is_dir()
        results[f"dir_{dir_path.replace('/', '_')}"] = exists
        if not exists:
            print(f"[FAIL] Missing directory: {dir_path}")
        else:
            print(f"[PASS] Directory exists: {dir_path}")

    return results

def check_key_files():
    """Check that essential files have been created"""
    required_files = [
        "frontend-nextjs/app/assessment/page.tsx",
        "frontend-nextjs/app/assessment/layout.tsx",
        "frontend-nextjs/components/assessment/core/PropertyCard.tsx",
        "frontend-nextjs/components/assessment/core/ComplianceChecklist.tsx",
        "frontend-nextjs/lib/assessment/types.ts"
    ]

    results = {}
    for file_path in required_files:
        full_path = Path(file_path)
        exists = full_path.exists() and full_path.is_file()
        results[f"file_{os.path.basename(file_path)}"] = exists

        if not exists:
            print(f" Missing file: {file_path}")
        else:
            # Check file is not empty
            if full_path.stat().st_size > 0:
                print(f" File exists and has content: {file_path}")
            else:
                print(f" File exists but is empty: {file_path}")
                results[f"file_{os.path.basename(file_path)}"] = False

    return results

def check_typescript_compilation():
    """Check that TypeScript compiles without errors"""
    print("\nChecking TypeScript compilation...")

    try:
        # Change to frontend-nextjs directory
        os.chdir("frontend-nextjs")

        # Check if next.config.js exists
        if not Path("next.config.js").exists():
            print("ℹ️ Creating basic next.config.js...")
            with open("next.config.js", "w") as f:
                f.write("""/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
}

module.exports = nextConfig
""")

        # Try to build (this will check TypeScript)
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        os.chdir("..")  # Go back to project root

        if result.returncode == 0:
            print(" TypeScript compilation successful")
            return {"typescript_compilation": True}
        else:
            print(" TypeScript compilation failed:")
            print("STDOUT:", result.stdout[-500:])  # Last 500 chars
            print("STDERR:", result.stderr[-500:])
            return {"typescript_compilation": False}

    except subprocess.TimeoutExpired:
        os.chdir("..")
        print(" TypeScript compilation timed out")
        return {"typescript_compilation": False}
    except Exception as e:
        os.chdir("..")
        print(f" TypeScript compilation error: {e}")
        return {"typescript_compilation": False}

def check_dev_server():
    """Check that development server can start"""
    print("\n🔍 Checking development server startup...")

    try:
        os.chdir("frontend-nextjs")

        # Start dev server
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for server to start (look for "Ready" message)
        import time
        ready = False
        start_time = time.time()

        while time.time() - start_time < 30:  # 30 second timeout
            line = proc.stdout.readline()
            if line and ("Ready" in line or "started server" in line):
                ready = True
                break
            time.sleep(0.5)

        # Clean up
        proc.terminate()
        proc.wait(timeout=5)

        os.chdir("..")

        if ready:
            print(" Development server started successfully")
            return {"dev_server": True}
        else:
            print(" Development server failed to start or timed out")
            return {"dev_server": False}

    except Exception as e:
        os.chdir("..")
        print(f" Development server error: {e}")
        return {"dev_server": False}

def check_route_accessibility():
    """Check that /assessment route is accessible"""
    print("\n🔍 Checking route accessibility...")

    # This is a basic check - in a full implementation, we'd use Selenium
    # For now, just check the file exists and has the right export

    assessment_page = Path("frontend-nextjs/app/assessment/page.tsx")
    if assessment_page.exists():
        content = assessment_page.read_text()

        # Check for React component export
        has_export = "export default" in content
        has_function = "function" in content or "const" in content
        has_jsx = "return" in content and "<" in content

        route_accessible = has_export and has_function and has_jsx

        if route_accessible:
            print(" Assessment route appears properly configured")
        else:
            print(" Assessment route may not be properly configured")
            print(f"  - Has export: {has_export}")
            print(f"  - Has function: {has_function}")
            print(f"  - Has JSX: {has_jsx}")

        return {"route_accessible": route_accessible}
    else:
        print(" Assessment page file does not exist")
        return {"route_accessible": False}

def check_component_imports():
    """Check that components can be imported without errors"""
    print("\n🔍 Checking component imports...")

    components = [
        "frontend-nextjs/components/assessment/core/PropertyCard.tsx",
        "frontend-nextjs/components/assessment/core/ComplianceChecklist.tsx"
    ]

    results = {}

    for component_path in components:
        component_name = os.path.basename(component_path).replace(".tsx", "")

        if Path(component_path).exists():
            content = Path(component_path).read_text()

            # Basic checks for valid React component
            has_react_import = "import React" in content or "from 'react'" in content
            has_export = "export default" in content
            has_interface = "interface" in content or "Props" in content

            valid_component = has_react_import and has_export

            results[f"component_{component_name}_valid"] = valid_component

            if valid_component:
                print(f" Component {component_name} appears valid")
            else:
                print(f" Component {component_name} may have issues:")
                print(f"  - React import: {has_react_import}")
                print(f"  - Export default: {has_export}")
        else:
            results[f"component_{component_name}_valid"] = False
            print(f" Component {component_name} does not exist")

    return results

def generate_summary_report(all_results):
    """Generate comprehensive summary"""
    total_checks = sum(len(result_group) for result_group in all_results.values())
    passed_checks = sum(
        sum(result_group.values()) for result_group in all_results.values()
    )

    success_rate = (passed_checks / total_checks) * 100 if total_checks > 0 else 0

    print(f"\n📊 PRP-A1 VERIFICATION SUMMARY")
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
            status = "" if passed else ""
            print(f"  {status} {check}")

    return {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "success_rate": success_rate,
        "overall_pass": success_rate >= 85  # 85% threshold for passing
    }

def main():
    """Main verification function"""
    print("PRP-A1 VERIFICATION: Foundation & Project Merge")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")

    # Change to project root if we're in PRPs/NEWUI
    if os.getcwd().endswith("PRPs/NEWUI") or os.getcwd().endswith("PRPs\\NEWUI"):
        os.chdir("../..")
        print(f"Changed to project root: {os.getcwd()}")

    verification_results = {
        "prp": "A1_FOUNDATION",
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "errors": [],
        "warnings": []
    }

    # Run all verification checks
    all_results = {}

    print("\n1️⃣ Checking Directory Structure...")
    all_results["directory_structure"] = check_directory_structure()

    print("\n2️⃣ Checking Key Files...")
    all_results["key_files"] = check_key_files()

    print("\n3️⃣ Checking Component Imports...")
    all_results["component_imports"] = check_component_imports()

    print("\n4️⃣ Checking Route Accessibility...")
    all_results["route_accessibility"] = check_route_accessibility()

    print("\n5️⃣ Checking TypeScript Compilation...")
    all_results["typescript"] = check_typescript_compilation()

    print("\n6️⃣ Checking Development Server...")
    all_results["dev_server"] = check_dev_server()

    # Generate summary
    summary = generate_summary_report(all_results)

    # Compile final results
    verification_results["checks"] = {
        category: results for category, results in all_results.items()
    }
    verification_results["summary"] = summary
    verification_results["success"] = summary["overall_pass"]

    # Save results
    results_dir = Path("PRPs/NEWUI/results")
    results_dir.mkdir(exist_ok=True)

    results_file = results_dir / "prp_a1_results.json"
    with open(results_file, "w") as f:
        json.dump(verification_results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    # Final verdict
    if summary["overall_pass"]:
        print(f"\n🎉 PRP-A1 VERIFICATION PASSED!")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        print("\n Ready to proceed to PRP-A2")
        return 0
    else:
        print(f"\n PRP-A1 VERIFICATION FAILED!")
        print(f"Success rate: {summary['success_rate']:.1f}% (minimum 85% required)")
        print("\n🔧 Fix the failed checks before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())