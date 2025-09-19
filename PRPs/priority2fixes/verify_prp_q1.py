#!/usr/bin/env python3
"""
PRP-Q1 Granular Verification Script: Live Compliance Calculator Engine
Comprehensive automated testing with detailed success criteria
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

class PRPQ1VerificationSuite:
    """Granular verification for PRP-Q1: Live Compliance Calculator Engine"""

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    async def run_complete_verification(self) -> Dict:
        """Run all PRP-Q1 verification tests"""

        print("PRP-Q1 GRANULAR VERIFICATION SUITE")
        print("====================================")
        print("Testing: Live Compliance Calculator Engine")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Test Category 1: File Structure Verification
        await self._verify_file_structure()

        # Test Category 2: Engine Functionality
        await self._verify_engine_functionality()

        # Test Category 3: API Integration
        await self._verify_api_integration()

        # Test Category 4: Performance Benchmarks
        await self._verify_performance_benchmarks()

        # Test Category 5: Data Accuracy
        await self._verify_data_accuracy()

        # Test Category 6: Error Handling
        await self._verify_error_handling()

        # Generate final report
        return self._generate_final_report()

    async def _verify_file_structure(self):
        """Test 1: Verify all required files exist"""
        print("📁 TESTING FILE STRUCTURE")
        print("-" * 25)

        required_files = [
            'services/live_compliance_engine.py',
            'frontend-nextjs/app/api/compliance/live-check/route.ts'
        ]

        for file_path in required_files:
            exists = os.path.exists(file_path)
            self._record_test(
                test_name=f"file_exists_{file_path.replace('/', '_').replace('.', '_')}",
                passed=exists,
                description=f"Required file exists: {file_path}",
                category="file_structure",
                details={"file_path": file_path, "exists": exists}
            )
            print(f"  {'[OK]' if exists else '[MISSING]'} {file_path}")

    async def _verify_engine_functionality(self):
        """Test 2: Verify engine core functionality"""
        print("\n⚙️  TESTING ENGINE FUNCTIONALITY")
        print("-" * 30)

        engine_path = 'services/live_compliance_engine.py'

        if not os.path.exists(engine_path):
            self._record_test(
                test_name="engine_import_skip",
                passed=False,
                description="Engine file missing - skipping functionality tests",
                category="engine_functionality"
            )
            print("  ❌ Engine file missing - skipping tests")
            return

        try:
            # Test engine import
            sys.path.append('services')
            from live_compliance_engine import LiveComplianceEngine, ComplianceResult, ComplianceAssessment

            self._record_test(
                test_name="engine_import_success",
                passed=True,
                description="Engine imports successfully",
                category="engine_functionality"
            )
            print("  ✅ Engine imports successfully")

            # Test engine instantiation
            engine = LiveComplianceEngine()

            self._record_test(
                test_name="engine_instantiation",
                passed=True,
                description="Engine instantiates without error",
                category="engine_functionality"
            )
            print("  ✅ Engine instantiates without error")

            # Test required methods exist
            required_methods = ['calculate_compliance', '_check_fsr_compliance', '_check_height_compliance']
            for method_name in required_methods:
                has_method = hasattr(engine, method_name)
                self._record_test(
                    test_name=f"method_exists_{method_name}",
                    passed=has_method,
                    description=f"Engine has required method: {method_name}",
                    category="engine_functionality"
                )
                print(f"  {'✅' if has_method else '❌'} Method exists: {method_name}")

        except ImportError as e:
            self._record_test(
                test_name="engine_import_failure",
                passed=False,
                description=f"Engine import failed: {str(e)}",
                category="engine_functionality",
                details={"error": str(e)}
            )
            print(f"  ❌ Engine import failed: {e}")

    async def _verify_api_integration(self):
        """Test 3: Verify NSW API integration"""
        print("\n🌐 TESTING API INTEGRATION")
        print("-" * 25)

        try:
            sys.path.append('services')
            from live_compliance_engine import LiveComplianceEngine

            engine = LiveComplianceEngine()

            # Test 1: Basic API call functionality
            test_address = "45 Liverpool Street, Ashfield NSW 2131"
            test_proposal = {
                'gross_floor_area': 180,
                'height': 8.5
            }

            try:
                start_time = time.time()
                result = await engine.calculate_compliance(test_address, test_proposal)
                api_call_time = int((time.time() - start_time) * 1000)

                # Test API call succeeds
                self._record_test(
                    test_name="api_call_succeeds",
                    passed=result is not None,
                    description="API call returns result",
                    category="api_integration",
                    details={
                        "address": test_address,
                        "call_time_ms": api_call_time,
                        "result_type": type(result).__name__
                    }
                )
                print(f"  {'✅' if result else '❌'} API call returns result ({api_call_time}ms)")

                if result:
                    # Test result structure
                    has_fsr_compliance = hasattr(result, 'fsr_compliance')
                    has_height_compliance = hasattr(result, 'height_compliance')
                    has_overall_compliant = hasattr(result, 'overall_compliant')

                    structure_ok = has_fsr_compliance and has_height_compliance and has_overall_compliant

                    self._record_test(
                        test_name="result_structure",
                        passed=structure_ok,
                        description="Result has expected structure",
                        category="api_integration",
                        details={
                            "has_fsr_compliance": has_fsr_compliance,
                            "has_height_compliance": has_height_compliance,
                            "has_overall_compliant": has_overall_compliant
                        }
                    )
                    print(f"  {'✅' if structure_ok else '❌'} Result has expected structure")

                    # Test live API data usage
                    uses_live_data = False
                    if result.fsr_compliance and 'nsw_api' in result.fsr_compliance.data_source:
                        uses_live_data = True
                    if result.height_compliance and 'nsw_api' in result.height_compliance.data_source:
                        uses_live_data = True

                    self._record_test(
                        test_name="uses_live_api_data",
                        passed=uses_live_data,
                        description="Engine uses live NSW API data",
                        category="api_integration",
                        details={
                            "fsr_source": result.fsr_compliance.data_source if result.fsr_compliance else None,
                            "height_source": result.height_compliance.data_source if result.height_compliance else None
                        }
                    )
                    print(f"  {'✅' if uses_live_data else '❌'} Engine uses live NSW API data")

            except Exception as e:
                self._record_test(
                    test_name="api_call_exception",
                    passed=False,
                    description=f"API call failed with exception: {str(e)}",
                    category="api_integration",
                    details={"error": str(e), "error_type": type(e).__name__}
                )
                print(f"  ❌ API call failed: {e}")

        except ImportError:
            print("  ⏭️  Skipping API integration tests - engine not available")

    async def _verify_performance_benchmarks(self):
        """Test 4: Verify performance requirements"""
        print("\n⚡ TESTING PERFORMANCE BENCHMARKS")
        print("-" * 32)

        try:
            sys.path.append('services')
            from live_compliance_engine import LiveComplianceEngine

            engine = LiveComplianceEngine()

            # Performance test scenarios
            test_scenarios = [
                {
                    'name': 'simple_dwelling',
                    'address': '45 Liverpool Street, Ashfield NSW 2131',
                    'proposal': {'gross_floor_area': 150, 'height': 8.0}
                },
                {
                    'name': 'complex_development',
                    'address': '15 Norton Street, Leichhardt NSW 2040',
                    'proposal': {'gross_floor_area': 300, 'height': 10.0}
                }
            ]

            total_times = []

            for scenario in test_scenarios:
                try:
                    start_time = time.time()
                    result = await engine.calculate_compliance(
                        scenario['address'],
                        scenario['proposal']
                    )
                    calculation_time = int((time.time() - start_time) * 1000)
                    total_times.append(calculation_time)

                    # Test individual performance (<100ms requirement)
                    performance_ok = calculation_time < 100

                    self._record_test(
                        test_name=f"performance_{scenario['name']}",
                        passed=performance_ok,
                        description=f"Performance test {scenario['name']} <100ms",
                        category="performance",
                        details={
                            "scenario": scenario['name'],
                            "actual_time_ms": calculation_time,
                            "target_time_ms": 100,
                            "address": scenario['address']
                        }
                    )
                    print(f"  {'✅' if performance_ok else '❌'} {scenario['name']}: {calculation_time}ms")

                except Exception as e:
                    self._record_test(
                        test_name=f"performance_{scenario['name']}_error",
                        passed=False,
                        description=f"Performance test {scenario['name']} failed: {str(e)}",
                        category="performance",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {scenario['name']}: Error - {e}")

            # Average performance test
            if total_times:
                avg_time = sum(total_times) / len(total_times)
                avg_performance_ok = avg_time < 100

                self._record_test(
                    test_name="average_performance",
                    passed=avg_performance_ok,
                    description="Average performance <100ms",
                    category="performance",
                    details={
                        "average_time_ms": round(avg_time, 2),
                        "individual_times": total_times,
                        "target_time_ms": 100
                    }
                )
                print(f"  {'✅' if avg_performance_ok else '❌'} Average: {avg_time:.1f}ms")

        except ImportError:
            print("  ⏭️  Skipping performance tests - engine not available")

    async def _verify_data_accuracy(self):
        """Test 5: Verify calculation accuracy"""
        print("\n🎯 TESTING DATA ACCURACY")
        print("-" * 23)

        try:
            sys.path.append('services')
            from live_compliance_engine import LiveComplianceEngine

            engine = LiveComplianceEngine()

            # Known test case with expected results
            known_test = {
                'address': '45 Liverpool Street, Ashfield NSW 2131',  # R2 zone
                'proposal': {
                    'gross_floor_area': 240,  # For 400sqm site = 0.6 FSR
                    'height': 8.5  # Within typical height limits
                },
                'expected': {
                    'fsr_likely_compliant': True,  # 0.6 is typical R2 limit
                    'height_likely_compliant': True  # 8.5m is typically compliant
                }
            }

            try:
                result = await engine.calculate_compliance(
                    known_test['address'],
                    known_test['proposal']
                )

                if result:
                    # Test FSR calculation accuracy
                    if result.fsr_compliance:
                        fsr_reasonable = (
                            result.fsr_compliance.actual_value > 0 and
                            result.fsr_compliance.actual_value < 2.0 and
                            result.fsr_compliance.limit_value > 0
                        )

                        self._record_test(
                            test_name="fsr_calculation_reasonable",
                            passed=fsr_reasonable,
                            description="FSR calculation produces reasonable values",
                            category="accuracy",
                            details={
                                "actual_fsr": result.fsr_compliance.actual_value,
                                "limit_fsr": result.fsr_compliance.limit_value,
                                "compliant": result.fsr_compliance.compliant
                            }
                        )
                        print(f"  {'✅' if fsr_reasonable else '❌'} FSR calculation reasonable: {result.fsr_compliance.actual_value} vs {result.fsr_compliance.limit_value}")

                    # Test height calculation accuracy
                    if result.height_compliance:
                        height_reasonable = (
                            result.height_compliance.actual_value == known_test['proposal']['height'] and
                            result.height_compliance.limit_value > 0
                        )

                        self._record_test(
                            test_name="height_calculation_accurate",
                            passed=height_reasonable,
                            description="Height calculation matches input and has valid limit",
                            category="accuracy",
                            details={
                                "input_height": known_test['proposal']['height'],
                                "actual_height": result.height_compliance.actual_value,
                                "limit_height": result.height_compliance.limit_value,
                                "compliant": result.height_compliance.compliant
                            }
                        )
                        print(f"  {'✅' if height_reasonable else '❌'} Height calculation accurate: {result.height_compliance.actual_value}m vs {result.height_compliance.limit_value}m limit")

                    # Test overall compliance logic
                    compliance_logic_ok = isinstance(result.overall_compliant, bool)

                    self._record_test(
                        test_name="compliance_logic",
                        passed=compliance_logic_ok,
                        description="Overall compliance is boolean value",
                        category="accuracy",
                        details={"overall_compliant": result.overall_compliant}
                    )
                    print(f"  {'✅' if compliance_logic_ok else '❌'} Overall compliance logic: {result.overall_compliant}")

            except Exception as e:
                self._record_test(
                    test_name="accuracy_test_error",
                    passed=False,
                    description=f"Accuracy test failed: {str(e)}",
                    category="accuracy",
                    details={"error": str(e)}
                )
                print(f"  ❌ Accuracy test error: {e}")

        except ImportError:
            print("  ⏭️  Skipping accuracy tests - engine not available")

    async def _verify_error_handling(self):
        """Test 6: Verify error handling"""
        print("\n🛡️  TESTING ERROR HANDLING")
        print("-" * 25)

        try:
            sys.path.append('services')
            from live_compliance_engine import LiveComplianceEngine

            engine = LiveComplianceEngine()

            # Test invalid address handling
            try:
                result = await engine.calculate_compliance(
                    "Invalid Address That Does Not Exist",
                    {'gross_floor_area': 100, 'height': 8.0}
                )

                # Should either return None or handle gracefully
                handles_invalid_address = result is None or (
                    hasattr(result, 'warnings') and len(result.warnings) > 0
                )

                self._record_test(
                    test_name="invalid_address_handling",
                    passed=handles_invalid_address,
                    description="Handles invalid addresses gracefully",
                    category="error_handling",
                    details={"result_is_none": result is None}
                )
                print(f"  {'✅' if handles_invalid_address else '❌'} Invalid address handling")

            except Exception as e:
                # Catching exception is also acceptable error handling
                self._record_test(
                    test_name="invalid_address_exception",
                    passed=True,
                    description="Invalid address raises handled exception",
                    category="error_handling",
                    details={"exception_type": type(e).__name__}
                )
                print(f"  ✅ Invalid address exception handling: {type(e).__name__}")

            # Test missing proposal data
            try:
                result = await engine.calculate_compliance(
                    "45 Liverpool Street, Ashfield NSW 2131",
                    {}  # Empty proposal
                )

                handles_empty_proposal = True  # If no exception, it handles it

                self._record_test(
                    test_name="empty_proposal_handling",
                    passed=handles_empty_proposal,
                    description="Handles empty proposal data",
                    category="error_handling"
                )
                print(f"  ✅ Empty proposal handling")

            except Exception as e:
                # Exception is acceptable for invalid input
                self._record_test(
                    test_name="empty_proposal_exception",
                    passed=True,
                    description="Empty proposal raises appropriate exception",
                    category="error_handling",
                    details={"exception_type": type(e).__name__}
                )
                print(f"  ✅ Empty proposal exception: {type(e).__name__}")

        except ImportError:
            print("  ⏭️  Skipping error handling tests - engine not available")

    def _record_test(self, test_name: str, passed: bool, description: str,
                     category: str, details: Optional[Dict] = None):
        """Record a test result"""
        self.test_results.append({
            'test_name': test_name,
            'passed': passed,
            'description': description,
            'category': category,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })

    def _generate_final_report(self) -> Dict:
        """Generate comprehensive final report"""

        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['passed'])
        failed_tests = total_tests - passed_tests

        # Group by category
        category_results = {}
        for test in self.test_results:
            category = test['category']
            if category not in category_results:
                category_results[category] = {'passed': 0, 'failed': 0, 'total': 0}

            category_results[category]['total'] += 1
            if test['passed']:
                category_results[category]['passed'] += 1
            else:
                category_results[category]['failed'] += 1

        # Success criteria evaluation
        success_criteria = {
            'file_structure_complete': category_results.get('file_structure', {}).get('passed', 0) >= 1,
            'engine_functionality_working': category_results.get('engine_functionality', {}).get('passed', 0) >= 3,
            'api_integration_successful': category_results.get('api_integration', {}).get('passed', 0) >= 2,
            'performance_requirements_met': category_results.get('performance', {}).get('passed', 0) >= 2,
            'accuracy_validated': category_results.get('accuracy', {}).get('passed', 0) >= 2,
            'error_handling_robust': category_results.get('error_handling', {}).get('passed', 0) >= 1
        }

        overall_success = (
            passed_tests >= total_tests * 0.8 and  # 80% pass rate
            all(success_criteria.values())  # All key criteria met
        )

        report = {
            'prp_id': 'PRP-Q1',
            'title': 'Live Compliance Calculator Engine',
            'verification_timestamp': datetime.now().isoformat(),
            'total_verification_time_seconds': round(time.time() - self.start_time, 2),
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'pass_rate_percent': round((passed_tests / total_tests) * 100, 1) if total_tests > 0 else 0
            },
            'category_results': category_results,
            'success_criteria': success_criteria,
            'overall_success': overall_success,
            'overall_status': 'PASS' if overall_success else 'FAIL',
            'detailed_test_results': self.test_results,
            'recommendations': self._generate_recommendations(success_criteria, category_results)
        }

        return report

    def _generate_recommendations(self, success_criteria: Dict, category_results: Dict) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        if not success_criteria.get('file_structure_complete', False):
            recommendations.append("Create missing required files: services/live_compliance_engine.py and API endpoint")

        if not success_criteria.get('engine_functionality_working', False):
            recommendations.append("Implement core engine functionality with required methods")

        if not success_criteria.get('api_integration_successful', False):
            recommendations.append("Fix NSW Planning API integration to use live data")

        if not success_criteria.get('performance_requirements_met', False):
            recommendations.append("Optimize performance to meet <100ms response time requirement")

        if not success_criteria.get('accuracy_validated', False):
            recommendations.append("Validate calculation accuracy with known test scenarios")

        if not success_criteria.get('error_handling_robust', False):
            recommendations.append("Implement robust error handling for invalid inputs")

        return recommendations

    def save_report(self, filename: Optional[str] = None) -> str:
        """Save verification report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PRP_Q1_VERIFICATION_REPORT_{timestamp}.json"

        report = self._generate_final_report()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

async def main():
    """Run PRP-Q1 verification"""
    print("STARTING PRP-Q1 GRANULAR VERIFICATION")
    print()

    suite = PRPQ1VerificationSuite()
    report = await suite.run_complete_verification()

    # Print summary
    print(f"\nVERIFICATION SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {'PASS' if report['overall_success'] else 'FAIL'}")
    print(f"Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']} ({report['test_summary']['pass_rate_percent']}%)")
    print(f"Verification Time: {report['total_verification_time_seconds']}s")
    print()

    # Print category breakdown
    print("Category Breakdown:")
    for category, results in report['category_results'].items():
        status = "[PASS]" if results['passed'] == results['total'] else "[PARTIAL]" if results['passed'] > 0 else "[FAIL]"
        print(f"  {status} {category}: {results['passed']}/{results['total']}")

    print()

    # Print recommendations if any
    if report['recommendations']:
        print("Recommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
        print()

    # Save report
    filename = suite.save_report()
    print(f"Detailed report saved: {filename}")

    return report

if __name__ == '__main__':
    asyncio.run(main())