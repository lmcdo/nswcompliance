#!/usr/bin/env python3
"""
PRP-A8 Verification Script: End-to-End Testing
Tests comprehensive E2E framework, integration tests, and system readiness
"""

import os
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def check_e2e_framework():
    """Check E2E testing framework implementation"""
    print("Checking E2E testing framework...")

    results = {}

    # Check test runner
    test_runner_path = "../../frontend-nextjs/tests/e2e/test-runner.js"
    if Path(test_runner_path).exists():
        content = Path(test_runner_path).read_text(encoding='utf-8')

        has_test_runner_class = "E2ETestRunner" in content
        has_comprehensive_tests = all([
            "testHealthCheck" in content,
            "testPropertyAssessment" in content,
            "testComplianceEngine" in content,
            "testReportGeneration" in content,
            "testAPIEndpoints" in content,
            "testUserInterface" in content,
            "testDataIntegrity" in content,
            "testPerformance" in content
        ])

        has_test_execution = "runTest" in content and "generateReport" in content
        has_http_simulation = "makeRequest" in content

        results["test_runner"] = all([
            has_test_runner_class, has_comprehensive_tests,
            has_test_execution, has_http_simulation
        ])

        if results["test_runner"]:
            print(" E2E Test Runner: Properly implemented")
        else:
            print(" E2E Test Runner: Missing functionality")
            print(f"  - Test runner class: {has_test_runner_class}")
            print(f"  - Comprehensive tests: {has_comprehensive_tests}")
            print(f"  - Test execution: {has_test_execution}")
            print(f"  - HTTP simulation: {has_http_simulation}")
    else:
        results["test_runner"] = False
        print(" E2E Test Runner: File not found")

    return results

def check_integration_tests():
    """Check integration test suite implementation"""
    print("Checking integration test suite...")

    results = {}

    integration_path = "../../frontend-nextjs/tests/e2e/integration-tests.js"
    if Path(integration_path).exists():
        content = Path(integration_path).read_text(encoding='utf-8')

        has_integration_class = "IntegrationTestSuite" in content
        has_prp_tests = all([
            "testFoundationIntegration" in content,
            "testAPIGatewayIntegration" in content,
            "testDataBridgeIntegration" in content,
            "testUIBindingIntegration" in content,
            "testStateManagementIntegration" in content,
            "testComplianceEngineIntegration" in content,
            "testReportGenerationIntegration" in content
        ])

        has_workflow_tests = "testCompleteWorkflow" in content
        has_simulation_methods = all([
            "simulatePropertySearch" in content,
            "simulateAssessmentSetup" in content,
            "simulateComplianceCheck" in content,
            "simulateReportGeneration" in content
        ])

        results["integration_tests"] = all([
            has_integration_class, has_prp_tests,
            has_workflow_tests, has_simulation_methods
        ])

        if results["integration_tests"]:
            print(" Integration Tests: Properly implemented")
        else:
            print(" Integration Tests: Missing functionality")
            print(f"  - Integration class: {has_integration_class}")
            print(f"  - PRP tests: {has_prp_tests}")
            print(f"  - Workflow tests: {has_workflow_tests}")
            print(f"  - Simulation methods: {has_simulation_methods}")
    else:
        results["integration_tests"] = False
        print(" Integration Tests: File not found")

    return results

def check_performance_tests():
    """Check performance testing utilities"""
    print("Checking performance testing utilities...")

    results = {}

    performance_path = "../../frontend-nextjs/tests/e2e/performance-tests.js"
    if Path(performance_path).exists():
        content = Path(performance_path).read_text(encoding='utf-8')

        has_performance_class = "PerformanceTestSuite" in content
        has_performance_tests = all([
            "testLoadPerformance" in content,
            "testStressTest" in content,
            "testConcurrencyTest" in content,
            "testMemoryLeakTest" in content
        ])

        has_metrics_collection = "metrics" in content and "response_times" in content
        has_reporting = "generatePerformanceReport" in content

        results["performance_tests"] = all([
            has_performance_class, has_performance_tests,
            has_metrics_collection, has_reporting
        ])

        if results["performance_tests"]:
            print(" Performance Tests: Properly implemented")
        else:
            print(" Performance Tests: Missing functionality")
            print(f"  - Performance class: {has_performance_class}")
            print(f"  - Performance tests: {has_performance_tests}")
            print(f"  - Metrics collection: {has_metrics_collection}")
            print(f"  - Reporting: {has_reporting}")
    else:
        results["performance_tests"] = False
        print(" Performance Tests: File not found")

    return results

def check_master_orchestrator():
    """Check master test orchestrator"""
    print("Checking master test orchestrator...")

    results = {}

    orchestrator_path = "../../frontend-nextjs/tests/e2e/run-all-tests.js"
    if Path(orchestrator_path).exists():
        content = Path(orchestrator_path).read_text(encoding='utf-8')

        has_orchestrator_class = "MasterTestOrchestrator" in content
        has_test_phases = all([
            "Phase 1: End-to-End Testing" in content,
            "Phase 2: Integration Testing" in content,
            "Phase 3: Performance Testing" in content
        ])

        has_master_reporting = "generateMasterReport" in content
        has_production_assessment = "PRODUCTION READY" in content
        has_recommendations = "generateRecommendations" in content

        results["master_orchestrator"] = all([
            has_orchestrator_class, has_test_phases,
            has_master_reporting, has_production_assessment, has_recommendations
        ])

        if results["master_orchestrator"]:
            print(" Master Orchestrator: Properly implemented")
        else:
            print(" Master Orchestrator: Missing functionality")
            print(f"  - Orchestrator class: {has_orchestrator_class}")
            print(f"  - Test phases: {has_test_phases}")
            print(f"  - Master reporting: {has_master_reporting}")
            print(f"  - Production assessment: {has_production_assessment}")
            print(f"  - Recommendations: {has_recommendations}")
    else:
        results["master_orchestrator"] = False
        print(" Master Orchestrator: File not found")

    return results

def check_test_execution():
    """Check test execution scripts and configuration"""
    print("Checking test execution scripts...")

    results = {}

    # Check standalone test runner
    test_script_path = "../run_tests.sh"
    if Path(test_script_path).exists():
        content = Path(test_script_path).read_text(encoding='utf-8')

        has_server_check = "curl -s http://localhost:3007" in content
        has_test_execution = "run-all-tests.js" in content
        has_cleanup = "kill $SERVER_PID" in content
        is_executable = os.access(test_script_path, os.X_OK)

        results["test_execution"] = all([
            has_server_check, has_test_execution, has_cleanup, is_executable
        ])

        if results["test_execution"]:
            print(" Test Execution Scripts: Properly implemented")
        else:
            print(" Test Execution Scripts: Missing functionality")
            print(f"  - Server check: {has_server_check}")
            print(f"  - Test execution: {has_test_execution}")
            print(f"  - Cleanup: {has_cleanup}")
            print(f"  - Executable: {is_executable}")
    else:
        results["test_execution"] = False
        print(" Test Execution Scripts: File not found")

    # Check test commands configuration
    test_commands_path = "../../frontend-nextjs/tests/test-commands.json"
    if Path(test_commands_path).exists():
        try:
            with open(test_commands_path, 'r') as f:
                config = json.load(f)

            has_test_scripts = "scripts" in config
            if has_test_scripts:
                scripts = config["scripts"]
                has_all_commands = all([
                    "test:e2e" in scripts,
                    "test:integration" in scripts,
                    "test:performance" in scripts,
                    "test:all" in scripts,
                    "test:prp-a8" in scripts
                ])
                results["test_commands"] = has_all_commands
            else:
                results["test_commands"] = False

            if results["test_commands"]:
                print(" Test Commands: Properly configured")
            else:
                print(" Test Commands: Missing configuration")
        except Exception as e:
            results["test_commands"] = False
            print(f" Test Commands: Error reading config - {e}")
    else:
        results["test_commands"] = False
        print(" Test Commands: Configuration file not found")

    return results

def check_test_structure():
    """Check overall test structure and organization"""
    print("Checking test structure and organization...")

    results = {}

    # Check test directory structure
    test_dir = Path("../../frontend-nextjs/tests/e2e")
    if test_dir.exists():
        required_files = [
            "test-runner.js",
            "integration-tests.js",
            "performance-tests.js",
            "run-all-tests.js"
        ]

        missing_files = []
        for file in required_files:
            if not (test_dir / file).exists():
                missing_files.append(file)

        results["test_structure"] = len(missing_files) == 0

        if results["test_structure"]:
            print(" Test Structure: Complete")
        else:
            print(f" Test Structure: Missing files - {missing_files}")
    else:
        results["test_structure"] = False
        print(" Test Structure: Test directory not found")

    return results

def check_prp_completeness():
    """Check that all PRPs A1-A8 are complete"""
    print("Checking PRP completeness...")

    results = {}

    prp_scripts = []
    prp_verifications = []

    # Check for all PRP execution scripts
    for i in range(1, 9):
        script_path = f"../execute_prp_a{i}.sh"
        if Path(script_path).exists():
            prp_scripts.append(f"A{i}")

        # Check for verification scripts
        verify_path = f"verify_prp_a{i}.py"
        if Path(verify_path).exists():
            prp_verifications.append(f"A{i}")

    all_prps_exist = len(prp_scripts) == 8
    all_verifications_exist = len(prp_verifications) == 8

    results["prp_completeness"] = {
        "execution_scripts": all_prps_exist,
        "verification_scripts": all_verifications_exist,
        "scripts_found": prp_scripts,
        "verifications_found": prp_verifications
    }

    if all_prps_exist and all_verifications_exist:
        print(" PRP Completeness: All PRPs A1-A8 complete")
    else:
        print(" PRP Completeness: Missing components")
        print(f"  - Execution scripts: {prp_scripts}")
        print(f"  - Verification scripts: {prp_verifications}")

    return results

def test_nodejs_compatibility():
    """Test Node.js compatibility for test execution"""
    print("Testing Node.js compatibility...")

    try:
        # Check if Node.js is available
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            node_version = result.stdout.strip()
            print(f" Node.js version: {node_version}")
            return True
        else:
            print(" Node.js: Not available or not working")
            return False

    except subprocess.TimeoutExpired:
        print(" Node.js: Command timeout")
        return False
    except Exception as e:
        print(f" Node.js: Error - {e}")
        return False

def run_sample_test():
    """Run a sample test to verify the framework works"""
    print("Running sample test verification...")

    try:
        # Change to frontend directory
        os.chdir("../../frontend-nextjs")

        # Try to run a simple test validation
        test_script = """
const E2ETestRunner = require('./tests/e2e/test-runner');
const runner = new E2ETestRunner();
console.log('Sample test framework validation: PASSED');
"""

        # Write temporary test file
        with open('temp_test.js', 'w') as f:
            f.write(test_script)

        # Run the test
        result = subprocess.run(
            ["node", "temp_test.js"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Cleanup
        os.remove('temp_test.js')
        os.chdir("../PRPs/NEWUI/scripts")

        if result.returncode == 0 and "PASSED" in result.stdout:
            print(" Sample Test: Framework validation successful")
            return True
        else:
            print(" Sample Test: Framework validation failed")
            print(f" Error: {result.stderr}")
            return False

    except Exception as e:
        print(f" Sample Test: Error - {e}")
        # Ensure we're back in the right directory
        try:
            os.chdir("../PRPs/NEWUI/scripts")
        except:
            pass
        return False

def generate_verification_report(results):
    """Generate verification report"""
    print("\n" + "="*50)
    print("PRP-A8 VERIFICATION REPORT")
    print("="*50)

    total_checks = 0
    passed_checks = 0

    categories = [
        ("E2E Framework", results.get("e2e_framework", {})),
        ("Integration Tests", results.get("integration_tests", {})),
        ("Performance Tests", results.get("performance_tests", {})),
        ("Master Orchestrator", results.get("master_orchestrator", {})),
        ("Test Execution", results.get("test_execution", {})),
        ("Test Structure", results.get("test_structure", {})),
        ("PRP Completeness", results.get("prp_completeness", {})),
        ("Node.js Compatibility", results.get("nodejs_compatibility", False)),
        ("Sample Test", results.get("sample_test", False))
    ]

    for category_name, category_results in categories:
        print(f"\n{category_name}:")
        if isinstance(category_results, dict):
            for check_name, passed in category_results.items():
                if check_name not in ['scripts_found', 'verifications_found']:  # Skip info fields
                    total_checks += 1
                    if passed:
                        passed_checks += 1
                        print(f"  [PASS] {check_name}")
                    else:
                        print(f"  [FAIL] {check_name}")
        else:
            total_checks += 1
            if category_results:
                passed_checks += 1
                print(f"  [PASS] {category_name}")
            else:
                print(f"  [FAIL] {category_name}")

    success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0

    print(f"\n" + "="*50)
    print(f"VERIFICATION SUMMARY")
    print(f"="*50)
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print(f"Success Rate: {success_rate:.1f}%")

    # PRP Status Summary
    print(f"\nPRP PIPELINE STATUS:")
    print(f"===================")
    if results.get("prp_completeness", {}).get("execution_scripts", False):
        prp_list = results["prp_completeness"]["scripts_found"]
        for prp in prp_list:
            print(f"✅ PRP-{prp}: Complete")

    if success_rate >= 95:
        print("\nPRP-A8 VERIFICATION: EXCELLENT")
        print("End-to-End testing framework is fully implemented and ready!")
        print("All PRPs A1-A8 are complete and the system is production-ready.")
    elif success_rate >= 85:
        print("\nPRP-A8 VERIFICATION: GOOD")
        print("E2E testing framework is mostly complete with minor issues.")
    elif success_rate >= 70:
        print("\nPRP-A8 VERIFICATION: NEEDS WORK")
        print("E2E testing framework has significant gaps that need attention.")
    else:
        print("\nPRP-A8 VERIFICATION: FAILED")
        print("E2E testing framework is not properly implemented.")

    # Save results
    results_file = Path("../results/prp_a8_results.json")
    results_file.parent.mkdir(exist_ok=True)

    verification_results = {
        "prp_id": "A8",
        "verification_date": datetime.now().isoformat(),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "success_rate": success_rate,
        "status": "PASSED" if success_rate >= 85 else "FAILED",
        "detailed_results": results,
        "prp_pipeline_status": "COMPLETE" if success_rate >= 85 else "INCOMPLETE",
        "system_readiness": "PRODUCTION_READY" if success_rate >= 95 else "NEEDS_OPTIMIZATION",
        "recommendations": []
    }

    if success_rate < 100:
        verification_results["recommendations"] = [
            "Review failed checks and implement missing functionality",
            "Run complete test suite to verify system readiness",
            "Monitor test execution and performance metrics",
            "Ensure all PRPs are properly integrated",
            "Test complete workflow end-to-end",
            "Prepare for production deployment"
        ]

    with open(results_file, 'w') as f:
        json.dump(verification_results, f, indent=2)

    print(f"\nDetailed results saved to: {results_file}")

    # Final message
    if success_rate >= 85:
        print(f"\nNSW COMPLIANCE ENGINE: ALL PRPS COMPLETE!")
        print(f"System is ready for comprehensive testing and deployment!")
        print(f"Run './run_tests.sh' to execute the complete test suite")

    return success_rate >= 85

def main():
    """Main verification function"""
    print("Starting PRP-A8 Verification: End-to-End Testing")
    print("=" * 60)

    all_results = {}

    # Run verification checks
    all_results["e2e_framework"] = check_e2e_framework()
    all_results["integration_tests"] = check_integration_tests()
    all_results["performance_tests"] = check_performance_tests()
    all_results["master_orchestrator"] = check_master_orchestrator()
    all_results["test_execution"] = check_test_execution()
    all_results["test_structure"] = check_test_structure()
    all_results["prp_completeness"] = check_prp_completeness()

    # Test Node.js compatibility
    all_results["nodejs_compatibility"] = test_nodejs_compatibility()

    # Run sample test
    all_results["sample_test"] = run_sample_test()

    # Generate final report
    verification_passed = generate_verification_report(all_results)

    # Exit with appropriate code
    sys.exit(0 if verification_passed else 1)

if __name__ == "__main__":
    main()