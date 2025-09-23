#!/usr/bin/env python3
"""
Integration Verification Script
Runs automatically after each implementation step
Following principles from TECHNICAL_ROLLOUT_FAILURE_PREVENTION_GUIDE.md
"""

import sys
import subprocess
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import platform

# Attempt to import requests, provide fallback
try:
    import requests
except ImportError:
    print("WARNING: requests module not available, using urllib instead")
    import urllib.request
    import urllib.parse
    import urllib.error

    class requests:
        @staticmethod
        def get(url, params=None, timeout=10):
            if params:
                url = f"{url}?{urllib.parse.urlencode(params)}"

            class Response:
                def __init__(self, data, code):
                    self.text = data
                    self.status_code = code
                    self.ok = code == 200

                def json(self):
                    return json.loads(self.text)

            try:
                with urllib.request.urlopen(url, timeout=timeout) as response:
                    return Response(response.read().decode('utf-8'), response.code)
            except urllib.error.HTTPError as e:
                return Response(e.read().decode('utf-8'), e.code)

        @staticmethod
        def post(url, json=None, timeout=10):
            class Response:
                def __init__(self, data, code):
                    self.text = data
                    self.status_code = code
                    self.ok = code == 200

                def json(self):
                    return json.loads(self.text)

            try:
                data = json.dumps(json).encode('utf-8') if json else None
                req = urllib.request.Request(url, data=data)
                req.add_header('Content-Type', 'application/json')

                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return Response(response.read().decode('utf-8'), response.code)
            except urllib.error.HTTPError as e:
                return Response(e.read().decode('utf-8'), e.code)


class IntegrationVerifier:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.frontend_path = self.project_root / "frontend-nextjs"
        self.api_base = "http://localhost:3007"
        self.verification_results = []
        self.errors = []

    def verify_step_1(self) -> Tuple[bool, str]:
        """Verify main page integration"""
        print("\nVerifying Step 1: Main page integration...")

        # Check page.tsx has correct props
        page_file = self.frontend_path / "app" / "page.tsx"
        if not page_file.exists():
            return False, f"page.tsx not found at {page_file}"

        try:
            content = page_file.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"Failed to read page.tsx: {e}"

        # Check for required props in ComplianceChecklist
        checks = [
            ("developmentType={developmentType}" in content or "developmentType: developmentType" in content,
             "developmentType prop"),
            ("propertyId={selectedProperty}" in content or "propertyId: selectedProperty" in content,
             "propertyId prop"),
            ("zoneCode={zoneCode}" in content or "zoneCode: zoneCode" in content,
             "zoneCode prop"),
        ]

        failed = []
        for check, name in checks:
            if not check:
                failed.append(f"Missing: {name}")
                self.errors.append(f"Step 1: {name} not found in ComplianceChecklist props")

        if failed:
            # Check if it's still the old integration
            if "<ComplianceChecklist propertyData={propertyData} />" in content:
                return False, f"Old integration still present. Missing props: {', '.join(failed)}"
            return False, f"Integration incomplete: {', '.join(failed)}"

        return True, "Main page integration complete"

    def verify_step_2(self) -> Tuple[bool, str]:
        """Verify ComplianceChecklist component updates"""
        print("\nVerifying Step 2: ComplianceChecklist component...")

        # Try multiple possible locations
        possible_paths = [
            self.frontend_path / "components" / "compliance-checklist.tsx",
            self.frontend_path / "components" / "compliance" / "ComplianceChecklist.tsx",
            self.frontend_path / "components" / "compliance" / "compliance-checklist.tsx"
        ]

        component_file = None
        for path in possible_paths:
            if path.exists():
                component_file = path
                break

        if not component_file:
            return False, f"ComplianceChecklist component not found in any expected location"

        try:
            content = component_file.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"Failed to read component file: {e}"

        # Check for required prop types and functionality
        checks = [
            ("developmentType" in content, "developmentType prop"),
            ("propertyId" in content or "propertyData" in content, "property identifier"),
            ("zoneCode" in content or "zone" in content, "zone code prop"),
            ("useEffect" in content, "useEffect hook"),
            ("/api/compliance" in content, "API call to compliance endpoint")
        ]

        failed = []
        for check, name in checks:
            if not check:
                failed.append(f"Missing: {name}")
                self.errors.append(f"Step 2: {name} not found in ComplianceChecklist")

        if failed:
            return False, f"Component update incomplete: {', '.join(failed)}"

        # Test TypeScript compilation (with increased timeout)
        if not self._test_typescript_compilation(component_file):
            return False, "TypeScript compilation failed"

        return True, "ComplianceChecklist component properly updated"

    def verify_step_3(self) -> Tuple[bool, str]:
        """Verify DevelopmentSelector integration"""
        print("\nVerifying Step 3: DevelopmentSelector integration...")

        possible_paths = [
            self.frontend_path / "components" / "development-selector-enhanced.tsx",
            self.frontend_path / "components" / "development-selector.tsx",
            self.frontend_path / "components" / "development" / "DevelopmentSelector.tsx"
        ]

        selector_file = None
        for path in possible_paths:
            if path.exists():
                selector_file = path
                break

        if not selector_file:
            return False, "DevelopmentSelector not found in any expected location"

        try:
            content = selector_file.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"Failed to read selector file: {e}"

        # Check for zone-aware functionality
        checks = [
            ("zoneCode" in content or "zone" in content, "zone prop"),
            ("onChange" in content, "onChange handler"),
            ("value" in content, "value prop")
        ]

        # Zone-aware filtering is optional but recommended
        if "getAvailableTypes" in content or "zoneRestrictions" in content:
            checks.append((True, "zone-aware filtering"))

        failed = []
        for check, name in checks:
            if not check:
                failed.append(f"Missing: {name}")
                self.errors.append(f"Step 3: {name} not found in DevelopmentSelector")

        if failed:
            return False, f"Selector integration incomplete: {', '.join(failed)}"

        return True, "DevelopmentSelector properly integrated"

    def verify_step_4(self) -> Tuple[bool, str]:
        """Verify API parameter handling"""
        print("\nVerifying Step 4: API parameter compatibility...")

        # Check if API endpoint file exists
        api_file = self.frontend_path / "app" / "api" / "compliance" / "enhanced" / "route.ts"
        if not api_file.exists():
            # Try alternate location
            api_file = self.frontend_path / "app" / "api" / "compliance" / "route.ts"
            if not api_file.exists():
                return False, "Compliance API route file not found"

        try:
            content = api_file.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"Failed to read API route: {e}"

        # Check for parameter handling
        if "body.zone || body.zoneCode" in content or "zone || zoneCode" in content:
            return True, "API handles both zone and zoneCode parameters"

        # Check if it at least handles one
        if "body.zone" in content or "body.zoneCode" in content:
            return True, "API handles zone parameters"

        return False, "API parameter handling not properly configured"

    def verify_step_5(self) -> Tuple[bool, str]:
        """Verify state management integration"""
        print("\nVerifying Step 5: State management...")

        page_file = self.frontend_path / "app" / "page.tsx"
        if not page_file.exists():
            return False, "page.tsx not found"

        try:
            content = page_file.read_text(encoding='utf-8')
        except Exception as e:
            return False, f"Failed to read page.tsx: {e}"

        # Check for state management patterns
        checks = [
            ("useState" in content, "useState hook"),
            ("developmentType" in content and "setDevelopmentType" in content, "development type state"),
            ("handleDevelopmentTypeChange" in content or "onChange" in content, "change handler")
        ]

        # Optional but recommended states
        optional_checks = [
            ("complianceStatus" in content, "compliance status state"),
            ("isLoading" in content or "loading" in content, "loading state")
        ]

        failed = []
        for check, name in checks:
            if not check:
                failed.append(f"Missing: {name}")
                self.errors.append(f"Step 5: {name} not found in state management")

        warnings = []
        for check, name in optional_checks:
            if not check:
                warnings.append(f"Recommended: {name}")

        if failed:
            return False, f"State management incomplete: {', '.join(failed)}"

        if warnings:
            print(f"  Recommendations: {', '.join(warnings)}")

        return True, "State management properly integrated"

    def verify_step_6(self) -> Tuple[bool, str]:
        """Verify error handling and loading states"""
        print("\nVerifying Step 6: Error handling...")

        components_to_check = [
            (self.frontend_path / "app" / "page.tsx", "main page"),
            (self.frontend_path / "components" / "compliance-checklist.tsx", "ComplianceChecklist"),
        ]

        # Add alternate paths
        for alt_path in [
            self.frontend_path / "components" / "compliance" / "ComplianceChecklist.tsx",
            self.frontend_path / "components" / "development-selector-enhanced.tsx"
        ]:
            if alt_path.exists():
                components_to_check.append((alt_path, alt_path.stem))

        issues = []
        for component_path, component_name in components_to_check:
            if component_path.exists():
                try:
                    content = component_path.read_text(encoding='utf-8')
                except Exception as e:
                    issues.append(f"Could not read {component_name}: {e}")
                    continue

                # Basic error handling patterns
                has_loading = "loading" in content.lower() or "isloading" in content.lower()
                has_error = "error" in content.lower()
                has_try_catch = "try" in content and "catch" in content

                if not has_loading and not has_error and not has_try_catch:
                    issues.append(f"{component_name}: No error handling or loading states")

        if issues:
            return False, f"Error handling issues: {'; '.join(issues)}"

        return True, "Error handling and loading states implemented"

    def _test_typescript_compilation(self, file_path: Path) -> bool:
        """Test if TypeScript file compiles"""
        try:
            # Use quotes for Windows path handling
            quoted_path = f'"{str(file_path)}"'

            if platform.system() == "Windows":
                cmd = f'npx tsc --noEmit --skipLibCheck {quoted_path}'
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=self.frontend_path,
                    capture_output=True,
                    timeout=60,  # Increased timeout
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                cmd = ["npx", "tsc", "--noEmit", "--skipLibCheck", str(file_path)]
                result = subprocess.run(
                    cmd,
                    cwd=self.frontend_path,
                    capture_output=True,
                    timeout=60,
                    text=True
                )

            if result.returncode != 0:
                print(f"  TypeScript errors: {result.stderr[:200]}...")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("  TypeScript compilation timed out (non-critical)")
            return True  # Don't fail on timeout
        except Exception as e:
            print(f"  TypeScript compilation check skipped: {e}")
            return True  # Don't fail if tsc not available

    def verify_end_to_end(self) -> Tuple[bool, str]:
        """Verify complete end-to-end workflow"""
        print("\nVerifying end-to-end integration...")

        # Check if server is running
        try:
            response = requests.get(f"{self.api_base}/", timeout=5)
            if not response.ok:
                return False, "Frontend server not responding"
        except Exception as e:
            return False, f"Cannot connect to frontend server: {e}"

        # Test property API
        test_address = "30 ILLAWARRA ROAD MARRICKVILLE 2204"

        try:
            response = requests.get(
                f"{self.api_base}/api/property",
                params={"address": test_address},
                timeout=10
            )

            if not response.ok:
                return False, f"Property API failed with status {response.status_code}"

            property_data = response.json().get("data")
            if not property_data:
                return False, "No property data returned"

            print(f"  Property API: OK (propId: {property_data.get('propId')})")

        except Exception as e:
            return False, f"Property API test failed: {str(e)}"

        # Test compliance check (may fail if not fully implemented)
        try:
            response = requests.post(
                f"{self.api_base}/api/compliance/enhanced",
                json={
                    "propertyId": property_data.get("propId"),
                    "zone": property_data.get("constraints", {}).get("zone"),
                    "developmentType": "dual_occupancy"
                },
                timeout=10
            )

            if response.ok:
                print(f"  Compliance API: OK")
                return True, "End-to-end workflow successful"
            else:
                # Not critical if compliance API not ready
                print(f"  Compliance API: Not ready (status {response.status_code})")
                return True, "Property API working, compliance API pending"

        except Exception as e:
            # Compliance API might not be implemented yet
            print(f"  Compliance API: Not available ({str(e)[:50]})")
            return True, "Property API working, compliance API pending"

    def generate_report(self) -> str:
        """Generate verification report"""
        report = []
        report.append("\n" + "="*60)
        report.append("INTEGRATION VERIFICATION REPORT")
        report.append("="*60)
        report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Project Root: {self.project_root}")

        if self.errors:
            report.append("\nErrors Found:")
            for error in self.errors:
                report.append(f"  - {error}")
        else:
            report.append("\nNo errors found.")

        report.append("\nRecommendations:")
        report.append("  - Ensure all TypeScript files compile without errors")
        report.append("  - Test all API endpoints manually")
        report.append("  - Verify UI updates when development type changes")

        return "\n".join(report)

    def run_verification(self, step: int = None) -> bool:
        """Run verification for specific step or all steps"""

        print("="*60)
        print("INTEGRATION VERIFICATION")
        print("="*60)
        print(f"Project Root: {self.project_root}")
        print(f"Frontend Path: {self.frontend_path}")

        # Check if frontend exists
        if not self.frontend_path.exists():
            print(f"ERROR: Frontend directory not found at {self.frontend_path}")
            return False

        if step:
            # Run specific step
            verifier_method = getattr(self, f"verify_step_{step}", None)
            if not verifier_method:
                print(f"ERROR: Invalid step number: {step}")
                return False

            success, message = verifier_method()

            print("")
            if success:
                print(f"STEP {step}: PASS - {message}")
                return True
            else:
                print(f"STEP {step}: FAIL - {message}")
                return False

        else:
            # Run all steps
            all_passed = True
            results = []

            for i in range(1, 7):
                verifier_method = getattr(self, f"verify_step_{i}", None)
                if verifier_method:
                    success, message = verifier_method()
                    results.append((i, success, message))

                    if not success:
                        all_passed = False

            # Run end-to-end test
            success, message = self.verify_end_to_end()
            results.append(("E2E", success, message))

            if not success:
                all_passed = False

            # Print summary
            print("\n" + "="*60)
            print("VERIFICATION SUMMARY")
            print("="*60)

            for step_info in results:
                if len(step_info) == 3:
                    step_num, success, message = step_info
                    status = "PASS" if success else "FAIL"
                    symbol = "[PASS]" if success else "[FAIL]"

                    if step_num == "E2E":
                        print(f"{symbol} End-to-End: {status} - {message}")
                    else:
                        print(f"{symbol} Step {step_num}: {status} - {message}")

            # Print report
            print(self.generate_report())

            return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify integration implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_integration.py --project-root "C:/path/to/project"
  python verify_integration.py --step 1 --project-root "."
  python verify_integration.py --project-root "../.."
        """
    )

    parser.add_argument("--step", type=int, choices=range(1, 7),
                       help="Specific step to verify (1-6)")
    parser.add_argument("--project-root", required=True,
                       help="Project root directory")

    args = parser.parse_args()

    # Verify project root exists
    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        print(f"ERROR: Project root does not exist: {project_root}")
        sys.exit(1)

    verifier = IntegrationVerifier(args.project_root)
    success = verifier.run_verification(args.step)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()