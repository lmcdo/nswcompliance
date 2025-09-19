#!/usr/bin/env python3
"""
PRP-Q2 Granular Verification Script: Development Pathway Intelligence
Comprehensive automated testing with detailed success criteria
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

class PRPQ2VerificationSuite:
    """Granular verification for PRP-Q2: Development Pathway Intelligence"""

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    async def run_complete_verification(self) -> Dict:
        """Run all PRP-Q2 verification tests"""

        print("🎯 PRP-Q2 GRANULAR VERIFICATION SUITE")
        print("=====================================")
        print("Testing: Development Pathway Intelligence")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Test categories
        await self._verify_file_structure()
        await self._verify_engine_functionality()
        await self._verify_pathway_determination()
        await self._verify_sepp_integration()
        await self._verify_accuracy_benchmarks()
        await self._verify_performance_requirements()

        return self._generate_final_report()

    async def _verify_file_structure(self):
        """Test 1: Verify required files exist"""
        print("📁 TESTING FILE STRUCTURE")
        print("-" * 25)

        required_files = [
            'services/pathway_intelligence_engine.py',
            'frontend-nextjs/app/api/pathway/determine/route.ts'
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
            print(f"  {'✅' if exists else '❌'} {file_path}")

    async def _verify_engine_functionality(self):
        """Test 2: Verify engine core functionality"""
        print("\n⚙️  TESTING ENGINE FUNCTIONALITY")
        print("-" * 30)

        engine_path = 'services/pathway_intelligence_engine.py'

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
            from pathway_intelligence_engine import PathwayIntelligenceEngine, DevelopmentPathway, PathwayAssessment

            self._record_test(
                test_name="engine_import_success",
                passed=True,
                description="Engine imports successfully",
                category="engine_functionality"
            )
            print("  ✅ Engine imports successfully")

            # Test enum values
            pathway_enums = [
                DevelopmentPathway.EXEMPT,
                DevelopmentPathway.COMPLYING,
                DevelopmentPathway.DA_REQUIRED,
                DevelopmentPathway.PROHIBITED
            ]

            enum_test_passed = len(pathway_enums) == 4

            self._record_test(
                test_name="development_pathway_enum",
                passed=enum_test_passed,
                description="DevelopmentPathway enum has required values",
                category="engine_functionality",
                details={"enum_values": [p.value for p in pathway_enums]}
            )
            print(f"  {'✅' if enum_test_passed else '❌'} DevelopmentPathway enum complete")

            # Test engine instantiation
            engine = PathwayIntelligenceEngine()

            self._record_test(
                test_name="engine_instantiation",
                passed=True,
                description="Engine instantiates without error",
                category="engine_functionality"
            )
            print("  ✅ Engine instantiates without error")

            # Test required methods
            required_methods = ['determine_pathway', '_check_exempt', '_check_complying']
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

    async def _verify_pathway_determination(self):
        """Test 3: Verify pathway determination logic"""
        print("\n🎯 TESTING PATHWAY DETERMINATION")
        print("-" * 31)

        try:
            sys.path.append('services')
            from pathway_intelligence_engine import PathwayIntelligenceEngine, DevelopmentPathway

            engine = PathwayIntelligenceEngine()

            # Test scenarios with expected outcomes
            test_scenarios = [
                {
                    'name': 'exempt_dwelling_low_height',
                    'address': '45 Liverpool Street, Ashfield NSW 2131',
                    'development_type': 'dwelling_house',
                    'details': {'height': 7.5},
                    'expected_pathway': DevelopmentPathway.EXEMPT,
                    'rationale': 'Single dwelling under 8.5m should be exempt'
                },
                {
                    'name': 'complying_dwelling_within_limits',
                    'address': '15 Norton Street, Leichhardt NSW 2040',
                    'development_type': 'dwelling_house',
                    'details': {'height': 8.5, 'fsr': 0.5},
                    'expected_pathway': DevelopmentPathway.COMPLYING,
                    'rationale': 'Single dwelling within height and FSR limits should be complying'
                },
                {
                    'name': 'da_required_exceeds_limits',
                    'address': '25 King Street, Newtown NSW 2042',
                    'development_type': 'dwelling_house',
                    'details': {'height': 12.0, 'fsr': 1.5},
                    'expected_pathway': DevelopmentPathway.DA_REQUIRED,
                    'rationale': 'Development exceeding limits requires DA'
                }
            ]

            correct_determinations = 0
            total_scenarios = len(test_scenarios)

            for scenario in test_scenarios:
                try:
                    start_time = time.time()
                    result = await engine.determine_pathway(
                        scenario['address'],
                        scenario['development_type'],
                        scenario['details']
                    )
                    determination_time = int((time.time() - start_time) * 1000)

                    # Test pathway determination accuracy
                    pathway_correct = result.recommended_pathway == scenario['expected_pathway']
                    if pathway_correct:
                        correct_determinations += 1

                    # Test response time (<500ms requirement)
                    performance_ok = determination_time < 500

                    # Test result completeness
                    result_complete = all([
                        hasattr(result, 'recommended_pathway'),
                        hasattr(result, 'zone_confirmed'),
                        hasattr(result, 'confidence_score'),
                        hasattr(result, 'processing_time_ms')
                    ])

                    self._record_test(
                        test_name=f"pathway_determination_{scenario['name']}",
                        passed=pathway_correct and performance_ok and result_complete,
                        description=f"Pathway determination for {scenario['name']}",
                        category="pathway_determination",
                        details={
                            "scenario": scenario['name'],
                            "expected": scenario['expected_pathway'].value,
                            "actual": result.recommended_pathway.value,
                            "correct": pathway_correct,
                            "performance_ms": determination_time,
                            "confidence": result.confidence_score,
                            "zone": result.zone_confirmed
                        }
                    )

                    status = "✅" if (pathway_correct and performance_ok and result_complete) else "❌"
                    print(f"  {status} {scenario['name']}: {result.recommended_pathway.value} ({determination_time}ms)")

                except Exception as e:
                    self._record_test(
                        test_name=f"pathway_determination_{scenario['name']}_error",
                        passed=False,
                        description=f"Pathway determination {scenario['name']} failed: {str(e)}",
                        category="pathway_determination",
                        details={"error": str(e), "scenario": scenario['name']}
                    )
                    print(f"  ❌ {scenario['name']}: Error - {e}")

            # Overall pathway accuracy
            accuracy_percent = (correct_determinations / total_scenarios) * 100 if total_scenarios > 0 else 0
            accuracy_ok = accuracy_percent >= 90

            self._record_test(
                test_name="overall_pathway_accuracy",
                passed=accuracy_ok,
                description="Overall pathway determination accuracy ≥90%",
                category="pathway_determination",
                details={
                    "correct_determinations": correct_determinations,
                    "total_scenarios": total_scenarios,
                    "accuracy_percent": accuracy_percent,
                    "target_accuracy": 90
                }
            )
            print(f"  {'✅' if accuracy_ok else '❌'} Overall accuracy: {accuracy_percent:.1f}% (target: 90%)")

        except ImportError:
            print("  ⏭️  Skipping pathway determination tests - engine not available")

    async def _verify_sepp_integration(self):
        """Test 4: Verify SEPP integration"""
        print("\n📋 TESTING SEPP INTEGRATION")
        print("-" * 27)

        try:
            sys.path.append('services')
            from pathway_intelligence_engine import PathwayIntelligenceEngine

            engine = PathwayIntelligenceEngine()

            # Test SEPP (Housing) 2021 secondary dwelling logic
            secondary_dwelling_test = {
                'address': '45 Liverpool Street, Ashfield NSW 2131',
                'development_type': 'secondary_dwelling',
                'details': {'floor_area': 55}  # Under 60sqm limit
            }

            try:
                result = await engine.determine_pathway(
                    secondary_dwelling_test['address'],
                    secondary_dwelling_test['development_type'],
                    secondary_dwelling_test['details']
                )

                # Check if SEPP Housing 2021 is referenced
                sepp_housing_referenced = any(
                    'Housing' in sepp for sepp in result.applicable_sepps
                ) if result.applicable_sepps else False

                self._record_test(
                    test_name="sepp_housing_integration",
                    passed=sepp_housing_referenced,
                    description="SEPP (Housing) 2021 integration working",
                    category="sepp_integration",
                    details={
                        "applicable_sepps": result.applicable_sepps,
                        "pathway": result.recommended_pathway.value if result else None
                    }
                )
                print(f"  {'✅' if sepp_housing_referenced else '❌'} SEPP (Housing) 2021 integration")

            except Exception as e:
                self._record_test(
                    test_name="sepp_housing_integration_error",
                    passed=False,
                    description=f"SEPP Housing integration test failed: {str(e)}",
                    category="sepp_integration",
                    details={"error": str(e)}
                )
                print(f"  ❌ SEPP Housing integration error: {e}")

            # Test SEPP (Exempt and Complying Development Codes) 2008 integration
            exempt_test = {
                'address': '15 Norton Street, Leichhardt NSW 2040',
                'development_type': 'alterations_additions',
                'details': {'additional_floor_area': 35}  # Under 50sqm limit
            }

            try:
                result = await engine.determine_pathway(
                    exempt_test['address'],
                    exempt_test['development_type'],
                    exempt_test['details']
                )

                # Check pathway logic works
                pathway_logical = result.recommended_pathway in [
                    engine.DevelopmentPathway.EXEMPT,
                    engine.DevelopmentPathway.COMPLYING,
                    engine.DevelopmentPathway.DA_REQUIRED
                ]

                self._record_test(
                    test_name="exempt_complying_sepp_logic",
                    passed=pathway_logical,
                    description="SEPP Exempt/Complying logic functional",
                    category="sepp_integration",
                    details={
                        "pathway": result.recommended_pathway.value if result else None,
                        "applicable_sepps": result.applicable_sepps if result else None
                    }
                )
                print(f"  {'✅' if pathway_logical else '❌'} SEPP Exempt/Complying logic")

            except Exception as e:
                self._record_test(
                    test_name="exempt_complying_sepp_error",
                    passed=False,
                    description=f"SEPP Exempt/Complying test failed: {str(e)}",
                    category="sepp_integration",
                    details={"error": str(e)}
                )
                print(f"  ❌ SEPP Exempt/Complying error: {e}")

        except ImportError:
            print("  ⏭️  Skipping SEPP integration tests - engine not available")

    async def _verify_accuracy_benchmarks(self):
        """Test 5: Verify accuracy benchmarks"""
        print("\n🎯 TESTING ACCURACY BENCHMARKS")
        print("-" * 29)

        try:
            sys.path.append('services')
            from pathway_intelligence_engine import PathwayIntelligenceEngine, DevelopmentPathway

            engine = PathwayIntelligenceEngine()

            # Benchmark scenarios with high-confidence expected outcomes
            benchmark_scenarios = [
                {
                    'name': 'clear_exempt_case',
                    'address': '45 Liverpool Street, Ashfield NSW 2131',
                    'development_type': 'dwelling_house',
                    'details': {'height': 6.0},  # Well under 8.5m limit
                    'expected': DevelopmentPathway.EXEMPT,
                    'confidence_threshold': 0.8
                },
                {
                    'name': 'clear_da_required_case',
                    'address': '15 Norton Street, Leichhardt NSW 2040',
                    'development_type': 'dwelling_house',
                    'details': {'height': 15.0, 'fsr': 2.0},  # Clearly exceeds limits
                    'expected': DevelopmentPathway.DA_REQUIRED,
                    'confidence_threshold': 0.7
                }
            ]

            high_confidence_correct = 0
            total_benchmarks = len(benchmark_scenarios)

            for benchmark in benchmark_scenarios:
                try:
                    result = await engine.determine_pathway(
                        benchmark['address'],
                        benchmark['development_type'],
                        benchmark['details']
                    )

                    pathway_correct = result.recommended_pathway == benchmark['expected']
                    confidence_adequate = result.confidence_score >= benchmark['confidence_threshold']

                    if pathway_correct and confidence_adequate:
                        high_confidence_correct += 1

                    self._record_test(
                        test_name=f"accuracy_benchmark_{benchmark['name']}",
                        passed=pathway_correct and confidence_adequate,
                        description=f"Accuracy benchmark: {benchmark['name']}",
                        category="accuracy_benchmarks",
                        details={
                            "expected": benchmark['expected'].value,
                            "actual": result.recommended_pathway.value,
                            "correct": pathway_correct,
                            "confidence": result.confidence_score,
                            "confidence_threshold": benchmark['confidence_threshold'],
                            "confidence_adequate": confidence_adequate
                        }
                    )

                    status = "✅" if (pathway_correct and confidence_adequate) else "❌"
                    print(f"  {status} {benchmark['name']}: {result.recommended_pathway.value} (confidence: {result.confidence_score:.2f})")

                except Exception as e:
                    self._record_test(
                        test_name=f"accuracy_benchmark_{benchmark['name']}_error",
                        passed=False,
                        description=f"Accuracy benchmark {benchmark['name']} failed: {str(e)}",
                        category="accuracy_benchmarks",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {benchmark['name']}: Error - {e}")

            # High confidence accuracy rate
            hc_accuracy = (high_confidence_correct / total_benchmarks) * 100 if total_benchmarks > 0 else 0
            hc_accuracy_ok = hc_accuracy >= 95

            self._record_test(
                test_name="high_confidence_accuracy",
                passed=hc_accuracy_ok,
                description="High confidence scenarios ≥95% accuracy",
                category="accuracy_benchmarks",
                details={
                    "high_confidence_correct": high_confidence_correct,
                    "total_benchmarks": total_benchmarks,
                    "accuracy_percent": hc_accuracy,
                    "target_accuracy": 95
                }
            )
            print(f"  {'✅' if hc_accuracy_ok else '❌'} High confidence accuracy: {hc_accuracy:.1f}% (target: 95%)")

        except ImportError:
            print("  ⏭️  Skipping accuracy benchmark tests - engine not available")

    async def _verify_performance_requirements(self):
        """Test 6: Verify performance requirements"""
        print("\n⚡ TESTING PERFORMANCE REQUIREMENTS")
        print("-" * 34)

        try:
            sys.path.append('services')
            from pathway_intelligence_engine import PathwayIntelligenceEngine

            engine = PathwayIntelligenceEngine()

            # Performance test scenarios
            performance_tests = [
                {
                    'name': 'simple_determination',
                    'address': '45 Liverpool Street, Ashfield NSW 2131',
                    'development_type': 'dwelling_house',
                    'details': {'height': 8.0}
                },
                {
                    'name': 'complex_determination',
                    'address': '15 Norton Street, Leichhardt NSW 2040',
                    'development_type': 'residential_flat_building',
                    'details': {'height': 12.0, 'fsr': 0.8, 'storeys': 3}
                }
            ]

            performance_times = []

            for test in performance_tests:
                try:
                    start_time = time.time()
                    result = await engine.determine_pathway(
                        test['address'],
                        test['development_type'],
                        test['details']
                    )
                    determination_time = int((time.time() - start_time) * 1000)
                    performance_times.append(determination_time)

                    # Performance target: <500ms
                    performance_ok = determination_time < 500

                    self._record_test(
                        test_name=f"performance_{test['name']}",
                        passed=performance_ok,
                        description=f"Performance test {test['name']} <500ms",
                        category="performance",
                        details={
                            "actual_time_ms": determination_time,
                            "target_time_ms": 500,
                            "test_name": test['name']
                        }
                    )
                    print(f"  {'✅' if performance_ok else '❌'} {test['name']}: {determination_time}ms")

                except Exception as e:
                    self._record_test(
                        test_name=f"performance_{test['name']}_error",
                        passed=False,
                        description=f"Performance test {test['name']} failed: {str(e)}",
                        category="performance",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {test['name']}: Error - {e}")

            # Average performance
            if performance_times:
                avg_time = sum(performance_times) / len(performance_times)
                avg_performance_ok = avg_time < 500

                self._record_test(
                    test_name="average_performance",
                    passed=avg_performance_ok,
                    description="Average performance <500ms",
                    category="performance",
                    details={
                        "average_time_ms": round(avg_time, 2),
                        "individual_times": performance_times,
                        "target_time_ms": 500
                    }
                )
                print(f"  {'✅' if avg_performance_ok else '❌'} Average performance: {avg_time:.1f}ms")

        except ImportError:
            print("  ⏭️  Skipping performance tests - engine not available")

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
            'engine_functionality_working': category_results.get('engine_functionality', {}).get('passed', 0) >= 4,
            'pathway_determination_accurate': category_results.get('pathway_determination', {}).get('passed', 0) >= 3,
            'sepp_integration_functional': category_results.get('sepp_integration', {}).get('passed', 0) >= 1,
            'accuracy_benchmarks_met': category_results.get('accuracy_benchmarks', {}).get('passed', 0) >= 2,
            'performance_requirements_met': category_results.get('performance', {}).get('passed', 0) >= 2
        }

        overall_success = (
            passed_tests >= total_tests * 0.8 and  # 80% pass rate
            all(success_criteria.values())  # All key criteria met
        )

        report = {
            'prp_id': 'PRP-Q2',
            'title': 'Development Pathway Intelligence',
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
            recommendations.append("Create missing files: pathway_intelligence_engine.py and API endpoint")

        if not success_criteria.get('engine_functionality_working', False):
            recommendations.append("Implement core pathway determination engine with required methods and enums")

        if not success_criteria.get('pathway_determination_accurate', False):
            recommendations.append("Improve pathway determination accuracy to meet 90% target")

        if not success_criteria.get('sepp_integration_functional', False):
            recommendations.append("Implement SEPP integration for Housing 2021 and Exempt/Complying codes")

        if not success_criteria.get('accuracy_benchmarks_met', False):
            recommendations.append("Improve high-confidence scenario accuracy to 95%+ with appropriate confidence scoring")

        if not success_criteria.get('performance_requirements_met', False):
            recommendations.append("Optimize performance to meet <500ms response time requirement")

        return recommendations

    def save_report(self, filename: Optional[str] = None) -> str:
        """Save verification report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PRP_Q2_VERIFICATION_REPORT_{timestamp}.json"

        report = self._generate_final_report()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

async def main():
    """Run PRP-Q2 verification"""
    print("🚀 Starting PRP-Q2 Granular Verification")
    print()

    suite = PRPQ2VerificationSuite()
    report = await suite.run_complete_verification()

    # Print summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"Overall Status: {'✅ PASS' if report['overall_success'] else '❌ FAIL'}")
    print(f"Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']} ({report['test_summary']['pass_rate_percent']}%)")
    print(f"Verification Time: {report['total_verification_time_seconds']}s")
    print()

    # Print category breakdown
    print("📈 Category Breakdown:")
    for category, results in report['category_results'].items():
        status = "✅" if results['passed'] == results['total'] else "⚠️" if results['passed'] > 0 else "❌"
        print(f"  {status} {category}: {results['passed']}/{results['total']}")

    print()

    # Print recommendations if any
    if report['recommendations']:
        print("💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        print()

    # Save report
    filename = suite.save_report()
    print(f"📄 Detailed report saved: {filename}")

    return report

if __name__ == '__main__':
    asyncio.run(main())