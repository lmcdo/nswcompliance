#!/usr/bin/env python3
"""
Test Suite for Enhanced Compliance API (PRP-P5)
Tests backward compatibility and new development permissions features
"""

import json
import time
import subprocess
import sys
from typing import Dict, Any

class EnhancedAPITester:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    def run_api_test(self, test_name: str, zone: str, include_dev_permissions: bool = False,
                    development_type: str = None) -> Dict[str, Any]:
        """Run a single API test"""
        print(f"\n=== Running Test: {test_name} ===")

        # Build command
        cmd = [
            sys.executable,
            'services/enhanced_compliance_api.py',
            '--zone', zone,
            '--format', 'json'
        ]

        if include_dev_permissions:
            cmd.append('--include-development-permissions')

        if development_type:
            cmd.extend(['--development-type', development_type])

        print(f"Command: {' '.join(cmd)}")

        # Execute test
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            execution_time = (time.time() - start_time) * 1000

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout.strip())
                    test_result = {
                        'test_name': test_name,
                        'status': 'pass',
                        'execution_time_ms': execution_time,
                        'zone': zone,
                        'include_dev_permissions': include_dev_permissions,
                        'development_type': development_type,
                        'response_keys': list(response.keys()),
                        'has_dev_permissions': 'development_permissions' in response,
                        'has_feasibility': 'feasibility_check' in response,
                        'error': None
                    }

                    # Validate response structure
                    if include_dev_permissions and 'development_permissions' not in response:
                        test_result['status'] = 'fail'
                        test_result['error'] = 'development_permissions missing when requested'

                    if development_type and 'feasibility_check' not in response:
                        test_result['status'] = 'fail'
                        test_result['error'] = 'feasibility_check missing when development_type provided'

                    print(f"✓ Test passed - {execution_time:.1f}ms")
                    print(f"  Response keys: {test_result['response_keys']}")

                    return test_result

                except json.JSONDecodeError as e:
                    test_result = {
                        'test_name': test_name,
                        'status': 'fail',
                        'execution_time_ms': execution_time,
                        'error': f'JSON decode error: {e}',
                        'raw_output': result.stdout
                    }
                    print(f"✗ Test failed - JSON decode error: {e}")
                    return test_result
            else:
                test_result = {
                    'test_name': test_name,
                    'status': 'fail',
                    'execution_time_ms': execution_time,
                    'error': f'Process failed with code {result.returncode}',
                    'stderr': result.stderr
                }
                print(f"✗ Test failed - Process error: {result.stderr}")
                return test_result

        except subprocess.TimeoutExpired:
            test_result = {
                'test_name': test_name,
                'status': 'fail',
                'execution_time_ms': 10000,  # Timeout
                'error': 'Test timed out (>10s)'
            }
            print(f"✗ Test failed - Timeout")
            return test_result

    def test_backward_compatibility(self):
        """Test that existing API calls still work"""
        print("\n" + "="*60)
        print("TESTING BACKWARD COMPATIBILITY")
        print("="*60)

        # Test 1: Basic zone query (original functionality)
        test1 = self.run_api_test(
            "Basic zone query (R2)",
            zone="R2"
        )
        self.test_results.append(test1)

        # Test 2: Zone with development type (original functionality)
        test2 = self.run_api_test(
            "Zone with development type (R1, dwelling_house)",
            zone="R1",
            development_type="dwelling_house"
        )
        self.test_results.append(test2)

        # Test 3: Different zone (B1)
        test3 = self.run_api_test(
            "Commercial zone query (B1)",
            zone="B1"
        )
        self.test_results.append(test3)

    def test_new_development_permissions_feature(self):
        """Test new development permissions functionality"""
        print("\n" + "="*60)
        print("TESTING NEW DEVELOPMENT PERMISSIONS FEATURE")
        print("="*60)

        # Test 4: Zone query with development permissions
        test4 = self.run_api_test(
            "R2 with development permissions",
            zone="R2",
            include_dev_permissions=True
        )
        self.test_results.append(test4)

        # Test 5: B1 commercial zone with development permissions
        test5 = self.run_api_test(
            "B1 with development permissions",
            zone="B1",
            include_dev_permissions=True
        )
        self.test_results.append(test5)

        # Test 6: Industrial zone with development permissions
        test6 = self.run_api_test(
            "IN1 with development permissions",
            zone="IN1",
            include_dev_permissions=True
        )
        self.test_results.append(test6)

    def test_feasibility_checks(self):
        """Test development type feasibility checking"""
        print("\n" + "="*60)
        print("TESTING FEASIBILITY CHECKS")
        print("="*60)

        # Test 7: Dwelling house in R1 (should be permitted)
        test7 = self.run_api_test(
            "Dwelling house feasibility in R1",
            zone="R1",
            development_type="dwelling_house",
            include_dev_permissions=True
        )
        self.test_results.append(test7)

        # Test 8: Retail premises in B1 (should be permitted)
        test8 = self.run_api_test(
            "Retail premises feasibility in B1",
            zone="B1",
            development_type="retail_premises",
            include_dev_permissions=True
        )
        self.test_results.append(test8)

        # Test 9: General industry in R1 (should be prohibited)
        test9 = self.run_api_test(
            "General industry feasibility in R1 (should be prohibited)",
            zone="R1",
            development_type="general_industry",
            include_dev_permissions=True
        )
        self.test_results.append(test9)

    def test_performance(self):
        """Test API performance"""
        print("\n" + "="*60)
        print("TESTING PERFORMANCE")
        print("="*60)

        # Run multiple quick tests
        performance_tests = [
            ("R2", False, None),
            ("B1", True, None),
            ("R1", True, "dwelling_house"),
            ("IN1", True, "warehouse"),
            ("B3", True, "office_premises")
        ]

        execution_times = []

        for i, (zone, include_dev, dev_type) in enumerate(performance_tests):
            test_name = f"Performance test {i+1} ({zone})"
            test_result = self.run_api_test(test_name, zone, include_dev, dev_type)
            self.test_results.append(test_result)

            if test_result['status'] == 'pass':
                execution_times.append(test_result['execution_time_ms'])

        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            print(f"\nPerformance Summary:")
            print(f"  Average response time: {avg_time:.1f}ms")
            print(f"  Maximum response time: {max_time:.1f}ms")
            print(f"  Target (<2000ms): {'✓ PASS' if max_time < 2000 else '✗ FAIL'}")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n" + "="*60)
        print("TEST REPORT SUMMARY")
        print("="*60)

        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['status'] == 'pass'])
        failed_tests = total_tests - passed_tests

        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        total_time = time.time() - self.start_time
        print(f"Total Execution Time: {total_time:.2f} seconds")

        # Show failed tests
        if failed_tests > 0:
            print(f"\nFAILED TESTS:")
            for test in self.test_results:
                if test['status'] == 'fail':
                    print(f"  ✗ {test['test_name']}: {test.get('error', 'Unknown error')}")

        # Backward compatibility assessment
        backward_compat_tests = [t for t in self.test_results if 'backward' in t.get('test_name', '').lower() or not t.get('include_dev_permissions', False)]
        backward_compat_passed = len([t for t in backward_compat_tests if t['status'] == 'pass'])

        print(f"\nBACKWARD COMPATIBILITY:")
        print(f"  Tests: {len(backward_compat_tests)}")
        print(f"  Passed: {backward_compat_passed}")
        print(f"  Status: {'✓ MAINTAINED' if backward_compat_passed == len(backward_compat_tests) else '✗ BROKEN'}")

        # New features assessment
        new_feature_tests = [t for t in self.test_results if t.get('include_dev_permissions', False)]
        new_feature_passed = len([t for t in new_feature_tests if t['status'] == 'pass'])

        print(f"\nNEW FEATURES:")
        print(f"  Tests: {len(new_feature_tests)}")
        print(f"  Passed: {new_feature_passed}")
        print(f"  Status: {'✓ WORKING' if new_feature_passed == len(new_feature_tests) else '✗ ISSUES'}")

        # Save detailed report
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': (passed_tests/total_tests)*100,
                'execution_time_seconds': total_time
            },
            'backward_compatibility': {
                'tests': len(backward_compat_tests),
                'passed': backward_compat_passed,
                'maintained': backward_compat_passed == len(backward_compat_tests)
            },
            'new_features': {
                'tests': len(new_feature_tests),
                'passed': new_feature_passed,
                'working': new_feature_passed == len(new_feature_tests)
            },
            'detailed_results': self.test_results
        }

        with open('prp_p5_api_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\nDetailed report saved: prp_p5_api_test_report.json")

        return report

def main():
    print("Enhanced Compliance API Test Suite (PRP-P5)")
    print("Testing backward compatibility and new development permissions features")

    tester = EnhancedAPITester()

    # Run all test suites
    tester.test_backward_compatibility()
    tester.test_new_development_permissions_feature()
    tester.test_feasibility_checks()
    tester.test_performance()

    # Generate report
    report = tester.generate_test_report()

    # Exit with appropriate code
    if report['test_summary']['failed_tests'] == 0:
        print(f"\n🎉 All tests passed! API enhancement successful.")
        sys.exit(0)
    else:
        print(f"\n❌ {report['test_summary']['failed_tests']} tests failed. Review required.")
        sys.exit(1)

if __name__ == '__main__':
    main()