#!/usr/bin/env python3
"""
Master Verification Script for Authoritative Route UI Migration
Provides autocomplete functionality and detailed checking for each implementation phase.

Usage:
    python verify_ui_migration.py [phase] [--detailed] [--fix] [--report]

Phases:
    ui1 - Feature Flag System Implementation
    ui2 - DevelopmentSelector Component Migration
    ui3 - ComplianceStatus Component Migration
    ui4 - ComplianceChecklist Component Migration
    ui5 - Full Integration Testing and Optimization
    all - Run all phases
"""

import os
import sys
import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum

class VerificationStatus(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INFO = "INFO"
    PENDING = "PENDING"

@dataclass
class VerificationResult:
    check_name: str
    status: VerificationStatus
    message: str
    details: Optional[str] = None
    fix_suggestion: Optional[str] = None
    execution_time: float = 0.0

@dataclass
class PhaseResult:
    phase: str
    phase_name: str
    status: VerificationStatus
    checks: List[VerificationResult]
    start_time: datetime
    end_time: Optional[datetime] = None
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0

class UIVerificationFramework:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.frontend_path = self.project_root / "frontend-nextjs"
        self.prp_path = self.project_root / "PRPs" / "NEWUI" / "AUTHORITATIVErouteUI"
        self.results: List[PhaseResult] = []

        # Expected file structure for each phase
        self.phase_structure = {
            "ui1": {
                "name": "Feature Flag System Implementation",
                "files": [
                    "lib/feature-flags.ts",
                    "lib/feature-flag-service.ts",
                    "lib/feature-flag-safeguards.ts",
                    "components/providers/FeatureFlagProvider.tsx",
                    "components/debug/FeatureFlagDebugPanel.tsx",
                    "config/feature-flags.development.json"
                ],
                "tests": [
                    "__tests__/lib/feature-flags.test.ts",
                    "__tests__/components/FeatureFlagProvider.test.tsx"
                ],
                "apis": []
            },
            "ui2": {
                "name": "DevelopmentSelector Component Migration",
                "files": [
                    "components/development/DevelopmentSelector.tsx",
                    "components/development/EnhancedDevelopmentSelector.tsx",
                    "components/development/DevelopmentCard.tsx",
                    "contexts/DevelopmentContext.tsx",
                    "store/slices/developmentSlice.ts"
                ],
                "tests": [
                    "__tests__/components/development/DevelopmentSelector.test.tsx",
                    "__tests__/contexts/DevelopmentContext.test.tsx"
                ],
                "apis": [
                    "pages/api/development-types.ts"
                ]
            },
            "ui3": {
                "name": "ComplianceStatus Component Migration",
                "files": [
                    "components/compliance/ComplianceStatus.tsx",
                    "components/compliance/EnhancedComplianceStatus.tsx",
                    "components/compliance/ComplianceMetricCard.tsx",
                    "components/compliance/ComplianceProgressBar.tsx",
                    "contexts/ComplianceContext.tsx",
                    "lib/compliance-websocket.ts"
                ],
                "tests": [
                    "__tests__/components/compliance/ComplianceStatus.test.tsx",
                    "__tests__/lib/compliance-websocket.test.ts"
                ],
                "apis": [
                    "pages/api/compliance/status.ts"
                ]
            },
            "ui4": {
                "name": "ComplianceChecklist Component Migration",
                "files": [
                    "components/compliance/ComplianceChecklist.tsx",
                    "components/compliance/EnhancedComplianceChecklist.tsx",
                    "components/compliance/ChecklistItem.tsx",
                    "components/compliance/EvidenceSection.tsx",
                    "contexts/ChecklistContext.tsx",
                    "lib/evidence-manager.ts"
                ],
                "tests": [
                    "__tests__/components/compliance/ComplianceChecklist.test.tsx",
                    "__tests__/lib/evidence-manager.test.ts"
                ],
                "apis": [
                    "pages/api/compliance/checklist.ts",
                    "pages/api/evidence/upload.ts"
                ]
            },
            "ui5": {
                "name": "Full Integration Testing and Optimization",
                "files": [
                    "lib/integration/migration-orchestrator.ts",
                    "lib/health/migration-health-check.ts",
                    "lib/error-tracking/migration-error-tracker.ts",
                    "lib/ab-testing/migration-ab-test.ts",
                    "components/feedback/MigrationFeedback.tsx"
                ],
                "tests": [
                    "tests/integration/authoritative-migration.test.tsx",
                    "tests/performance/migration-performance.test.ts",
                    "__tests__/lib/integration/migration-orchestrator.test.ts"
                ],
                "apis": []
            }
        }

    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)

    def print_result(self, result: VerificationResult, indent: int = 0):
        """Print formatted verification result"""
        prefix = "  " * indent
        status_color = {
            VerificationStatus.PASS: "\033[92m",      # Green
            VerificationStatus.FAIL: "\033[91m",      # Red
            VerificationStatus.WARNING: "\033[93m",   # Yellow
            VerificationStatus.INFO: "\033[94m",      # Blue
            VerificationStatus.PENDING: "\033[95m"    # Magenta
        }
        reset_color = "\033[0m"

        color = status_color.get(result.status, "")
        print(f"{prefix}{color}{result.status.value}{reset_color} {result.check_name}")

        if result.message:
            print(f"{prefix}    {result.message}")

        if result.details:
            print(f"{prefix}    Details: {result.details}")

        if result.fix_suggestion and result.status == VerificationStatus.FAIL:
            print(f"{prefix}    Fix: {result.fix_suggestion}")

        if result.execution_time > 0:
            print(f"{prefix}    Time: {result.execution_time:.2f}s")

    def check_file_exists(self, file_path: str, phase: str) -> VerificationResult:
        """Check if a file exists"""
        start_time = time.time()
        full_path = self.frontend_path / file_path

        if full_path.exists():
            status = VerificationStatus.PASS
            message = f"File exists: {file_path}"
            fix_suggestion = None
        else:
            status = VerificationStatus.FAIL
            message = f"Missing file: {file_path}"
            fix_suggestion = f"Create {file_path} according to {phase.upper()} specifications"

        return VerificationResult(
            check_name=f"File Existence: {file_path}",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_typescript_syntax(self, file_path: str) -> VerificationResult:
        """Check TypeScript file syntax"""
        start_time = time.time()
        full_path = self.frontend_path / file_path

        if not full_path.exists():
            return VerificationResult(
                check_name=f"TypeScript Syntax: {file_path}",
                status=VerificationStatus.FAIL,
                message="File does not exist",
                execution_time=time.time() - start_time
            )

        try:
            # Use TypeScript compiler to check syntax - Windows compatible
            import os
            import platform

            # On Windows, use shell=True for npx commands
            if platform.system() == "Windows":
                # Use quotes to prevent file path interpretation as command
                quoted_path = f'"{str(full_path)}"'
                cmd = f"npx tsc --noEmit --skipLibCheck {quoted_path}"
                result = subprocess.run(
                    cmd,
                    cwd=self.frontend_path,
                    capture_output=True,
                    text=True,
                    timeout=60,  # Increased timeout for larger files
                    shell=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit", "--skipLibCheck", str(full_path)],
                    cwd=self.frontend_path,
                    capture_output=True,
                    text=True,
                    timeout=60,  # Increased timeout for larger files
                    encoding='utf-8'
                )

            if result.returncode == 0:
                status = VerificationStatus.PASS
                message = "TypeScript syntax valid"
                fix_suggestion = None
            else:
                status = VerificationStatus.FAIL
                message = f"TypeScript errors found"
                fix_suggestion = f"Fix TypeScript errors: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            status = VerificationStatus.WARNING
            message = "TypeScript check timed out"
            fix_suggestion = "Check for performance issues in TypeScript compilation"
        except Exception as e:
            status = VerificationStatus.WARNING
            message = f"Could not verify TypeScript syntax: {str(e)}"
            fix_suggestion = "Ensure TypeScript compiler is available"

        return VerificationResult(
            check_name=f"TypeScript Syntax: {file_path}",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_imports(self, file_path: str, expected_imports: List[str]) -> VerificationResult:
        """Check if file contains expected imports"""
        start_time = time.time()
        full_path = self.frontend_path / file_path

        if not full_path.exists():
            return VerificationResult(
                check_name=f"Import Verification: {file_path}",
                status=VerificationStatus.FAIL,
                message="File does not exist",
                execution_time=time.time() - start_time
            )

        try:
            content = full_path.read_text()
            missing_imports = []

            for expected_import in expected_imports:
                if expected_import not in content:
                    missing_imports.append(expected_import)

            if not missing_imports:
                status = VerificationStatus.PASS
                message = "All expected imports found"
                fix_suggestion = None
            else:
                status = VerificationStatus.FAIL
                message = f"Missing imports: {', '.join(missing_imports)}"
                fix_suggestion = f"Add missing imports to {file_path}"

        except Exception as e:
            status = VerificationStatus.WARNING
            message = f"Could not read file: {str(e)}"
            fix_suggestion = "Check file permissions and encoding"

        return VerificationResult(
            check_name=f"Import Verification: {file_path}",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_test_coverage(self, test_files: List[str]) -> VerificationResult:
        """Check test file existence and basic structure"""
        start_time = time.time()
        missing_tests = []
        invalid_tests = []

        for test_file in test_files:
            full_path = self.frontend_path / test_file

            if not full_path.exists():
                missing_tests.append(test_file)
                continue

            try:
                content = full_path.read_text()
                # Basic test structure validation
                if "describe(" not in content or "test(" not in content and "it(" not in content:
                    invalid_tests.append(test_file)
            except Exception:
                invalid_tests.append(test_file)

        issues = []
        if missing_tests:
            issues.append(f"Missing: {', '.join(missing_tests)}")
        if invalid_tests:
            issues.append(f"Invalid structure: {', '.join(invalid_tests)}")

        if not issues:
            status = VerificationStatus.PASS
            message = "All test files present and valid"
            fix_suggestion = None
        else:
            status = VerificationStatus.FAIL
            message = "; ".join(issues)
            fix_suggestion = "Create missing test files and ensure proper test structure"

        return VerificationResult(
            check_name="Test Coverage",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_feature_flag_integration(self) -> VerificationResult:
        """Check feature flag integration in main components"""
        start_time = time.time()

        # Check if feature flags are properly integrated
        main_page_path = self.frontend_path / "app" / "page.tsx"
        layout_path = self.frontend_path / "app" / "layout.tsx"

        integration_issues = []

        if main_page_path.exists():
            try:
                content = main_page_path.read_text(encoding='utf-8')
                if "useFeatureFlags" not in content:
                    integration_issues.append("Main page missing feature flag integration")
            except Exception as e:
                integration_issues.append(f"Could not read main page file: {str(e)}")
        else:
            integration_issues.append("Main page file not found")

        if layout_path.exists():
            try:
                content = layout_path.read_text(encoding='utf-8')
                if "FeatureFlagProvider" not in content:
                    integration_issues.append("Layout missing FeatureFlagProvider")
            except Exception as e:
                integration_issues.append(f"Could not read layout file: {str(e)}")
        else:
            integration_issues.append("Layout file not found")

        if not integration_issues:
            status = VerificationStatus.PASS
            message = "Feature flag integration properly implemented"
            fix_suggestion = None
        else:
            status = VerificationStatus.FAIL
            message = "; ".join(integration_issues)
            fix_suggestion = "Integrate feature flags into main page and layout components"

        return VerificationResult(
            check_name="Feature Flag Integration",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_state_management(self) -> VerificationResult:
        """Check Redux/Context state management setup"""
        start_time = time.time()

        required_files = [
            "store/index.ts",
            "store/slices/developmentSlice.ts"
        ]

        missing_files = []
        for file_path in required_files:
            if not (self.frontend_path / file_path).exists():
                missing_files.append(file_path)

        if not missing_files:
            status = VerificationStatus.PASS
            message = "State management files present"
            fix_suggestion = None
        else:
            status = VerificationStatus.FAIL
            message = f"Missing state management files: {', '.join(missing_files)}"
            fix_suggestion = "Create Redux store and required slices"

        return VerificationResult(
            check_name="State Management Setup",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_api_endpoints(self, api_files: List[str]) -> VerificationResult:
        """Check API endpoint implementation"""
        start_time = time.time()
        missing_apis = []

        for api_file in api_files:
            if not (self.frontend_path / api_file).exists():
                missing_apis.append(api_file)

        if not missing_apis:
            status = VerificationStatus.PASS
            message = "All API endpoints implemented"
            fix_suggestion = None
        else:
            status = VerificationStatus.FAIL
            message = f"Missing API endpoints: {', '.join(missing_apis)}"
            fix_suggestion = "Implement missing API endpoints"

        return VerificationResult(
            check_name="API Endpoints",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def check_performance_requirements(self, phase: str) -> VerificationResult:
        """Check performance-related requirements"""
        start_time = time.time()

        performance_files = [
            "next.config.js",
            "package.json"
        ]

        issues = []

        # Check Next.js config for optimization settings
        config_path = self.frontend_path / "next.config.js"
        if config_path.exists():
            try:
                content = config_path.read_text()
                if "experimental" not in content and phase in ["ui4", "ui5"]:
                    issues.append("Missing performance optimizations in Next.js config")
            except Exception:
                issues.append("Could not read Next.js config")

        # Check package.json for required dependencies
        package_path = self.frontend_path / "package.json"
        if package_path.exists():
            try:
                with open(package_path) as f:
                    package_data = json.load(f)

                required_deps = ["react", "next", "@reduxjs/toolkit"]
                missing_deps = []

                for dep in required_deps:
                    if dep not in package_data.get("dependencies", {}):
                        missing_deps.append(dep)

                if missing_deps:
                    issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

            except Exception:
                issues.append("Could not read package.json")

        if not issues:
            status = VerificationStatus.PASS
            message = "Performance requirements met"
            fix_suggestion = None
        else:
            status = VerificationStatus.WARNING
            message = "; ".join(issues)
            fix_suggestion = "Address performance configuration issues"

        return VerificationResult(
            check_name="Performance Requirements",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def run_unit_tests(self, phase: str) -> VerificationResult:
        """Run unit tests for the phase"""
        start_time = time.time()

        try:
            # Run Jest tests - Windows compatible
            import platform

            # On Windows, use shell=True for npm commands
            if platform.system() == "Windows":
                cmd = "npm test -- --passWithNoTests --watchAll=false"
                result = subprocess.run(
                    cmd,
                    cwd=self.frontend_path,
                    capture_output=True,
                    text=True,
                    shell=True,
                    timeout=120,
                    encoding='utf-8',
                    errors='replace'
                )
            else:
                result = subprocess.run(
                    ["npm", "test", "--", "--passWithNoTests", "--watchAll=false"],
                    cwd=self.frontend_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    encoding='utf-8'
                )

            if result.returncode == 0:
                status = VerificationStatus.PASS
                message = "Unit tests passed"
                fix_suggestion = None
            else:
                status = VerificationStatus.FAIL
                message = "Unit tests failed"
                fix_suggestion = f"Fix failing tests: {result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            status = VerificationStatus.WARNING
            message = "Unit tests timed out"
            fix_suggestion = "Optimize test performance or increase timeout"
        except Exception as e:
            status = VerificationStatus.WARNING
            message = f"Could not run unit tests: {str(e)}"
            fix_suggestion = "Ensure Jest and test environment are properly configured"

        return VerificationResult(
            check_name=f"Unit Tests ({phase.upper()})",
            status=status,
            message=message,
            fix_suggestion=fix_suggestion,
            execution_time=time.time() - start_time
        )

    def verify_phase(self, phase: str, detailed: bool = False) -> PhaseResult:
        """Verify a specific migration phase"""
        if phase not in self.phase_structure:
            raise ValueError(f"Unknown phase: {phase}")

        phase_info = self.phase_structure[phase]
        phase_result = PhaseResult(
            phase=phase,
            phase_name=phase_info["name"],
            status=VerificationStatus.PENDING,
            checks=[],
            start_time=datetime.now()
        )

        self.print_header(f"Verifying {phase.upper()}: {phase_info['name']}")

        # File existence checks
        for file_path in phase_info["files"]:
            result = self.check_file_exists(file_path, phase)
            phase_result.checks.append(result)
            if detailed:
                self.print_result(result, indent=1)

        # TypeScript syntax checks for .ts/.tsx files
        for file_path in phase_info["files"]:
            if file_path.endswith(('.ts', '.tsx')):
                result = self.check_typescript_syntax(file_path)
                phase_result.checks.append(result)
                if detailed:
                    self.print_result(result, indent=1)

        # Test coverage checks
        if phase_info["tests"]:
            result = self.check_test_coverage(phase_info["tests"])
            phase_result.checks.append(result)
            if detailed:
                self.print_result(result, indent=1)

        # API endpoint checks
        if phase_info["apis"]:
            result = self.check_api_endpoints(phase_info["apis"])
            phase_result.checks.append(result)
            if detailed:
                self.print_result(result, indent=1)

        # Phase-specific checks
        if phase == "ui1":
            result = self.check_feature_flag_integration()
            phase_result.checks.append(result)
            if detailed:
                self.print_result(result, indent=1)

        elif phase in ["ui2", "ui3", "ui4"]:
            result = self.check_state_management()
            phase_result.checks.append(result)
            if detailed:
                self.print_result(result, indent=1)

        # Performance requirements
        result = self.check_performance_requirements(phase)
        phase_result.checks.append(result)
        if detailed:
            self.print_result(result, indent=1)

        # Unit tests (if requested)
        if detailed:
            result = self.run_unit_tests(phase)
            phase_result.checks.append(result)
            self.print_result(result, indent=1)

        # Calculate results
        phase_result.end_time = datetime.now()
        phase_result.total_checks = len(phase_result.checks)

        for check in phase_result.checks:
            if check.status == VerificationStatus.PASS:
                phase_result.passed_checks += 1
            elif check.status == VerificationStatus.FAIL:
                phase_result.failed_checks += 1
            elif check.status == VerificationStatus.WARNING:
                phase_result.warning_checks += 1

        # Determine overall phase status
        if phase_result.failed_checks == 0:
            if phase_result.warning_checks == 0:
                phase_result.status = VerificationStatus.PASS
            else:
                phase_result.status = VerificationStatus.WARNING
        else:
            phase_result.status = VerificationStatus.FAIL

        return phase_result

    def generate_report(self, results: List[PhaseResult]) -> str:
        """Generate detailed verification report"""
        report = []
        report.append("# UI Migration Verification Report")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # Summary
        total_phases = len(results)
        passed_phases = sum(1 for r in results if r.status == VerificationStatus.PASS)
        failed_phases = sum(1 for r in results if r.status == VerificationStatus.FAIL)
        warning_phases = sum(1 for r in results if r.status == VerificationStatus.WARNING)

        report.append("## Summary")
        report.append(f"- Total Phases: {total_phases}")
        report.append(f"- Passed: {passed_phases}")
        report.append(f"- Failed: {failed_phases}")
        report.append(f"- Warnings: {warning_phases}")
        report.append("")

        # Detailed results
        for result in results:
            report.append(f"## {result.phase.upper()}: {result.phase_name}")
            report.append(f"Status: {result.status.value}")
            report.append(f"Checks: {result.passed_checks}/{result.total_checks} passed")

            if result.end_time:
                duration = (result.end_time - result.start_time).total_seconds()
                report.append(f"Duration: {duration:.2f}s")

            report.append("")

            if result.failed_checks > 0:
                report.append("### Failed Checks:")
                for check in result.checks:
                    if check.status == VerificationStatus.FAIL:
                        report.append(f"- {check.check_name}: {check.message}")
                        if check.fix_suggestion:
                            report.append(f"  Fix: {check.fix_suggestion}")
                report.append("")

            if result.warning_checks > 0:
                report.append("### Warnings:")
                for check in result.checks:
                    if check.status == VerificationStatus.WARNING:
                        report.append(f"- {check.check_name}: {check.message}")
                report.append("")

        return "\n".join(report)

    def save_report(self, report: str, filename: str = None):
        """Save verification report to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ui_migration_verification_{timestamp}.md"

        report_path = self.prp_path / filename
        report_path.write_text(report)
        print(f"\nReport saved to: {report_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Verify UI Migration Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_ui_migration.py ui1 --detailed
  python verify_ui_migration.py all --report
  python verify_ui_migration.py ui3 --fix --detailed
        """
    )

    parser.add_argument(
        "phase",
        choices=["ui1", "ui2", "ui3", "ui4", "ui5", "all"],
        help="Migration phase to verify"
    )

    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Show detailed verification output"
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show fix suggestions for failed checks"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and save verification report"
    )

    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory (default: current directory)"
    )

    args = parser.parse_args()

    # Initialize verification framework
    try:
        verifier = UIVerificationFramework(args.project_root)
    except Exception as e:
        print(f"Error initializing verifier: {e}")
        sys.exit(1)

    # Run verification
    results = []

    if args.phase == "all":
        phases = ["ui1", "ui2", "ui3", "ui4", "ui5"]
    else:
        phases = [args.phase]

    for phase in phases:
        try:
            result = verifier.verify_phase(phase, detailed=args.detailed)
            results.append(result)

            # Print summary
            print(f"\n{result.status.value} {result.phase.upper()}: {result.phase_name}")
            print(f"Checks: {result.passed_checks}/{result.total_checks} passed")

            if result.failed_checks > 0 and args.fix:
                print("\nFix suggestions:")
                for check in result.checks:
                    if check.status == VerificationStatus.FAIL and check.fix_suggestion:
                        print(f"  • {check.fix_suggestion}")

        except Exception as e:
            print(f"Error verifying {phase}: {e}")
            continue

    # Generate report if requested
    if args.report and results:
        report = verifier.generate_report(results)
        verifier.save_report(report)

    # Exit with appropriate code
    failed_phases = sum(1 for r in results if r.status == VerificationStatus.FAIL)
    sys.exit(failed_phases)

if __name__ == "__main__":
    main()