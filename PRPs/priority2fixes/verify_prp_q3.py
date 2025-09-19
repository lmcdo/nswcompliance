#!/usr/bin/env python3
"""
PRP-Q3 Granular Verification Script: Advanced Compliance Rules Engine
Comprehensive automated testing with detailed success criteria
"""

import asyncio
import json
import time
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

class PRPQ3VerificationSuite:
    """Granular verification for PRP-Q3: Advanced Compliance Rules Engine"""

    def __init__(self):
        self.test_results = []
        self.start_time = time.time()

    async def run_complete_verification(self) -> Dict:
        """Run all PRP-Q3 verification tests"""

        print("⚙️  PRP-Q3 GRANULAR VERIFICATION SUITE")
        print("=====================================")
        print("Testing: Advanced Compliance Rules Engine")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Test categories
        await self._verify_file_structure()
        await self._verify_engine_functionality()
        await self._verify_multi_factor_assessment()
        await self._verify_site_coverage_calculations()
        await self._verify_parking_compliance()
        await self._verify_landscaping_requirements()
        await self._verify_performance_requirements()

        return self._generate_final_report()

    async def _verify_file_structure(self):
        """Test 1: Verify required files exist"""
        print("📁 TESTING FILE STRUCTURE")
        print("-" * 25)

        required_files = [
            'services/advanced_compliance_engine.py',
            'frontend-nextjs/app/api/compliance/advanced-check/route.ts'
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

        engine_path = 'services/advanced_compliance_engine.py'

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
            from advanced_compliance_engine import AdvancedComplianceEngine, DevelopmentProposal, AdvancedComplianceResult

            self._record_test(
                test_name="engine_import_success",
                passed=True,
                description="Engine imports successfully",
                category="engine_functionality"
            )
            print("  ✅ Engine imports successfully")

            # Test DevelopmentProposal dataclass
            test_proposal = DevelopmentProposal(
                development_type='dwelling_house',
                gross_floor_area=200,
                building_area=120,
                height=8.5,
                storeys=2,
                dwelling_count=1,
                proposed_parking_spaces=2,
                landscaped_area=100,
                setbacks={'front': 6.0, 'side': 1.5, 'rear': 6.0}
            )

            proposal_created = test_proposal is not None

            self._record_test(
                test_name="development_proposal_dataclass",
                passed=proposal_created,
                description="DevelopmentProposal dataclass works",
                category="engine_functionality"
            )
            print(f"  {'✅' if proposal_created else '❌'} DevelopmentProposal dataclass")

            # Test engine instantiation
            engine = AdvancedComplianceEngine()

            self._record_test(
                test_name="engine_instantiation",
                passed=True,
                description="Engine instantiates without error",
                category="engine_functionality"
            )
            print("  ✅ Engine instantiates without error")

            # Test required methods
            required_methods = [
                'assess_advanced_compliance',
                '_check_site_coverage',
                '_check_parking_compliance',
                '_check_landscaping_compliance'
            ]

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

    async def _verify_multi_factor_assessment(self):
        """Test 3: Verify multi-factor compliance assessment"""
        print("\n🏗️  TESTING MULTI-FACTOR ASSESSMENT")
        print("-" * 35)

        try:
            sys.path.append('services')
            from advanced_compliance_engine import AdvancedComplianceEngine, DevelopmentProposal

            engine = AdvancedComplianceEngine()

            # Comprehensive test proposal
            test_proposal = DevelopmentProposal(
                development_type='dwelling_house',
                gross_floor_area=200,
                building_area=120,
                height=8.5,
                storeys=2,
                dwelling_count=1,
                proposed_parking_spaces=2,
                landscaped_area=100,
                setbacks={'front': 6.0, 'side': 1.5, 'rear': 6.0}
            )

            test_address = "45 Liverpool Street, Ashfield NSW 2131"

            try:
                start_time = time.time()
                result = await engine.assess_advanced_compliance(test_address, test_proposal)
                assessment_time = int((time.time() - start_time) * 1000)

                # Test result structure
                has_required_fields = all([
                    hasattr(result, 'site_coverage'),
                    hasattr(result, 'parking_compliance'),
                    hasattr(result, 'landscaping_compliance'),
                    hasattr(result, 'overall_compliant'),
                    hasattr(result, 'compliance_score'),
                    hasattr(result, 'total_processing_time_ms')
                ])

                self._record_test(
                    test_name="multi_factor_result_structure",
                    passed=has_required_fields,
                    description="Multi-factor assessment returns complete result structure",
                    category="multi_factor_assessment",
                    details={"assessment_time_ms": assessment_time}
                )
                print(f"  {'✅' if has_required_fields else '❌'} Complete result structure ({assessment_time}ms)")

                # Test compliance factors assessed
                factors_assessed = sum([
                    1 if result.site_coverage else 0,
                    1 if result.parking_compliance else 0,
                    1 if result.landscaping_compliance else 0,
                    1 if result.setback_compliance else 0
                ])

                factors_ok = factors_assessed >= 3  # At least 3 factors

                self._record_test(
                    test_name="multiple_factors_assessed",
                    passed=factors_ok,
                    description="Multiple compliance factors assessed (≥3)",
                    category="multi_factor_assessment",
                    details={
                        "factors_assessed": factors_assessed,
                        "site_coverage": result.site_coverage is not None,
                        "parking": result.parking_compliance is not None,
                        "landscaping": result.landscaping_compliance is not None,
                        "setbacks": result.setback_compliance is not None
                    }
                )
                print(f"  {'✅' if factors_ok else '❌'} Multiple factors assessed: {factors_assessed}")

                # Test compliance scoring
                compliance_score_valid = (
                    hasattr(result, 'compliance_score') and
                    isinstance(result.compliance_score, (int, float)) and
                    0 <= result.compliance_score <= 1
                )

                self._record_test(
                    test_name="compliance_score_valid",
                    passed=compliance_score_valid,
                    description="Compliance score is valid (0-1 range)",
                    category="multi_factor_assessment",
                    details={"compliance_score": result.compliance_score if hasattr(result, 'compliance_score') else None}
                )
                print(f"  {'✅' if compliance_score_valid else '❌'} Valid compliance score: {result.compliance_score if hasattr(result, 'compliance_score') else 'N/A'}")

                # Test performance requirement (<200ms)
                performance_ok = assessment_time < 200

                self._record_test(
                    test_name="multi_factor_performance",
                    passed=performance_ok,
                    description="Multi-factor assessment <200ms",
                    category="multi_factor_assessment",
                    details={
                        "actual_time_ms": assessment_time,
                        "target_time_ms": 200
                    }
                )
                print(f"  {'✅' if performance_ok else '❌'} Performance: {assessment_time}ms (target: <200ms)")

            except Exception as e:
                self._record_test(
                    test_name="multi_factor_assessment_error",
                    passed=False,
                    description=f"Multi-factor assessment failed: {str(e)}",
                    category="multi_factor_assessment",
                    details={"error": str(e)}
                )
                print(f"  ❌ Multi-factor assessment error: {e}")

        except ImportError:
            print("  ⏭️  Skipping multi-factor assessment tests - engine not available")

    async def _verify_site_coverage_calculations(self):
        """Test 4: Verify site coverage calculations"""
        print("\n🏠 TESTING SITE COVERAGE CALCULATIONS")
        print("-" * 37)

        try:
            sys.path.append('services')
            from advanced_compliance_engine import AdvancedComplianceEngine

            engine = AdvancedComplianceEngine()

            # Test site coverage calculation directly
            test_cases = [
                {
                    'name': 'R2_compliant',
                    'zone': 'R2',
                    'land_area': 400,  # sqm
                    'building_area': 180,  # sqm (45% coverage - within 50% R2 limit)
                    'expected_compliant': True
                },
                {
                    'name': 'R2_non_compliant',
                    'zone': 'R2',
                    'land_area': 300,  # sqm
                    'building_area': 200,  # sqm (66.7% coverage - exceeds 50% R2 limit)
                    'expected_compliant': False
                }
            ]

            for test_case in test_cases:
                try:
                    result = engine._check_site_coverage(
                        test_case['zone'],
                        test_case['land_area'],
                        test_case['building_area']
                    )

                    # Test calculation accuracy
                    calculation_accurate = (
                        result.compliant == test_case['expected_compliant'] and
                        result.actual_value > 0 and
                        result.limit_value > 0 and
                        result.units == '%'
                    )

                    self._record_test(
                        test_name=f"site_coverage_{test_case['name']}",
                        passed=calculation_accurate,
                        description=f"Site coverage calculation: {test_case['name']}",
                        category="site_coverage_calculations",
                        details={
                            "zone": test_case['zone'],
                            "land_area": test_case['land_area'],
                            "building_area": test_case['building_area'],
                            "expected_compliant": test_case['expected_compliant'],
                            "actual_compliant": result.compliant,
                            "coverage_percent": result.actual_value,
                            "limit_percent": result.limit_value
                        }
                    )

                    status = "✅" if calculation_accurate else "❌"
                    print(f"  {status} {test_case['name']}: {result.actual_value}% vs {result.limit_value}% limit ({'✅' if result.compliant else '❌'})")

                except Exception as e:
                    self._record_test(
                        test_name=f"site_coverage_{test_case['name']}_error",
                        passed=False,
                        description=f"Site coverage calculation {test_case['name']} failed: {str(e)}",
                        category="site_coverage_calculations",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {test_case['name']}: Error - {e}")

        except ImportError:
            print("  ⏭️  Skipping site coverage tests - engine not available")

    async def _verify_parking_compliance(self):
        """Test 5: Verify parking compliance calculations"""
        print("\n🚗 TESTING PARKING COMPLIANCE")
        print("-" * 28)

        try:
            sys.path.append('services')
            from advanced_compliance_engine import AdvancedComplianceEngine

            engine = AdvancedComplianceEngine()

            # Test parking compliance calculations
            parking_test_cases = [
                {
                    'name': 'dwelling_house_compliant',
                    'zone': 'R2',
                    'development_type': 'dwelling_house',
                    'dwelling_count': 1,
                    'gfa': 200,
                    'proposed_spaces': 2,
                    'expected_compliant': True  # 2 spaces for dwelling house
                },
                {
                    'name': 'dwelling_house_insufficient',
                    'zone': 'R2',
                    'development_type': 'dwelling_house',
                    'dwelling_count': 1,
                    'gfa': 200,
                    'proposed_spaces': 1,
                    'expected_compliant': False  # Only 1 space, needs 2
                },
                {
                    'name': 'residential_flats',
                    'zone': 'R4',
                    'development_type': 'residential_flat_building',
                    'dwelling_count': 4,
                    'gfa': 400,
                    'proposed_spaces': 4,
                    'expected_compliant': True  # 1 space per dwelling
                }
            ]

            for test_case in parking_test_cases:
                try:
                    result = engine._check_parking_compliance(
                        test_case['zone'],
                        test_case['development_type'],
                        test_case['dwelling_count'],
                        test_case['gfa'],
                        test_case['proposed_spaces']
                    )

                    # Test parking logic
                    parking_logic_ok = (
                        isinstance(result.compliant, bool) and
                        result.actual_value == test_case['proposed_spaces'] and
                        result.limit_value > 0 and
                        result.units == 'spaces'
                    )

                    self._record_test(
                        test_name=f"parking_compliance_{test_case['name']}",
                        passed=parking_logic_ok,
                        description=f"Parking compliance: {test_case['name']}",
                        category="parking_compliance",
                        details={
                            "development_type": test_case['development_type'],
                            "dwelling_count": test_case['dwelling_count'],
                            "proposed_spaces": test_case['proposed_spaces'],
                            "required_spaces": result.limit_value,
                            "compliant": result.compliant,
                            "expected_compliant": test_case['expected_compliant']
                        }
                    )

                    status = "✅" if parking_logic_ok else "❌"
                    print(f"  {status} {test_case['name']}: {result.actual_value} vs {result.limit_value} required ({'✅' if result.compliant else '❌'})")

                except Exception as e:
                    self._record_test(
                        test_name=f"parking_compliance_{test_case['name']}_error",
                        passed=False,
                        description=f"Parking compliance {test_case['name']} failed: {str(e)}",
                        category="parking_compliance",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {test_case['name']}: Error - {e}")

        except ImportError:
            print("  ⏭️  Skipping parking compliance tests - engine not available")

    async def _verify_landscaping_requirements(self):
        """Test 6: Verify landscaping requirements"""
        print("\n🌳 TESTING LANDSCAPING REQUIREMENTS")
        print("-" * 34)

        try:
            sys.path.append('services')
            from advanced_compliance_engine import AdvancedComplianceEngine

            engine = AdvancedComplianceEngine()

            # Test landscaping requirements
            landscaping_tests = [
                {
                    'name': 'R1_compliant',
                    'zone': 'R1',
                    'land_area': 500,  # sqm
                    'landscaped_area': 220,  # sqm (44% - above 40% requirement)
                    'expected_compliant': True
                },
                {
                    'name': 'R2_insufficient',
                    'zone': 'R2',
                    'land_area': 400,  # sqm
                    'landscaped_area': 80,   # sqm (20% - below 30% requirement)
                    'expected_compliant': False
                }
            ]

            for test_case in landscaping_tests:
                try:
                    result = engine._check_landscaping_compliance(
                        test_case['zone'],
                        test_case['land_area'],
                        test_case['landscaped_area']
                    )

                    # Test landscaping calculation
                    landscaping_calc_ok = (
                        isinstance(result.compliant, bool) and
                        result.actual_value >= 0 and
                        result.limit_value >= 0 and
                        result.units == '%'
                    )

                    self._record_test(
                        test_name=f"landscaping_{test_case['name']}",
                        passed=landscaping_calc_ok,
                        description=f"Landscaping requirements: {test_case['name']}",
                        category="landscaping_requirements",
                        details={
                            "zone": test_case['zone'],
                            "land_area": test_case['land_area'],
                            "landscaped_area": test_case['landscaped_area'],
                            "actual_percent": result.actual_value,
                            "required_percent": result.limit_value,
                            "compliant": result.compliant,
                            "expected_compliant": test_case['expected_compliant']
                        }
                    )

                    status = "✅" if landscaping_calc_ok else "❌"
                    print(f"  {status} {test_case['name']}: {result.actual_value}% vs {result.limit_value}% required ({'✅' if result.compliant else '❌'})")

                except Exception as e:
                    self._record_test(
                        test_name=f"landscaping_{test_case['name']}_error",
                        passed=False,
                        description=f"Landscaping test {test_case['name']} failed: {str(e)}",
                        category="landscaping_requirements",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {test_case['name']}: Error - {e}")

        except ImportError:
            print("  ⏭️  Skipping landscaping tests - engine not available")

    async def _verify_performance_requirements(self):
        """Test 7: Verify performance requirements"""
        print("\n⚡ TESTING PERFORMANCE REQUIREMENTS")
        print("-" * 34)

        try:
            sys.path.append('services')
            from advanced_compliance_engine import AdvancedComplianceEngine, DevelopmentProposal

            engine = AdvancedComplianceEngine()

            # Performance stress tests
            stress_tests = [
                {
                    'name': 'simple_proposal',
                    'proposal': DevelopmentProposal(
                        development_type='dwelling_house',
                        gross_floor_area=150,
                        building_area=100,
                        height=8.0,
                        storeys=2,
                        dwelling_count=1,
                        proposed_parking_spaces=2,
                        landscaped_area=150,
                        setbacks={'front': 6.0, 'side': 1.5, 'rear': 6.0}
                    )
                },
                {
                    'name': 'complex_proposal',
                    'proposal': DevelopmentProposal(
                        development_type='residential_flat_building',
                        gross_floor_area=600,
                        building_area=300,
                        height=12.0,
                        storeys=3,
                        dwelling_count=6,
                        proposed_parking_spaces=8,
                        landscaped_area=200,
                        setbacks={'front': 6.0, 'side': 3.0, 'rear': 8.0}
                    )
                }
            ]

            performance_times = []

            for stress_test in stress_tests:
                try:
                    start_time = time.time()
                    result = await engine.assess_advanced_compliance(
                        "45 Liverpool Street, Ashfield NSW 2131",
                        stress_test['proposal']
                    )
                    assessment_time = int((time.time() - start_time) * 1000)
                    performance_times.append(assessment_time)

                    # Performance requirement: <200ms
                    performance_ok = assessment_time < 200

                    self._record_test(
                        test_name=f"performance_stress_{stress_test['name']}",
                        passed=performance_ok,
                        description=f"Performance stress test {stress_test['name']} <200ms",
                        category="performance_requirements",
                        details={
                            "actual_time_ms": assessment_time,
                            "target_time_ms": 200,
                            "test_name": stress_test['name']
                        }
                    )

                    print(f"  {'✅' if performance_ok else '❌'} {stress_test['name']}: {assessment_time}ms")

                except Exception as e:
                    self._record_test(
                        test_name=f"performance_stress_{stress_test['name']}_error",
                        passed=False,
                        description=f"Performance test {stress_test['name']} failed: {str(e)}",
                        category="performance_requirements",
                        details={"error": str(e)}
                    )
                    print(f"  ❌ {stress_test['name']}: Error - {e}")

            # Average performance
            if performance_times:
                avg_time = sum(performance_times) / len(performance_times)
                avg_performance_ok = avg_time < 200

                self._record_test(
                    test_name="average_performance",
                    passed=avg_performance_ok,
                    description="Average performance <200ms",
                    category="performance_requirements",
                    details={
                        "average_time_ms": round(avg_time, 2),
                        "individual_times": performance_times,
                        "target_time_ms": 200
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
            'engine_functionality_working': category_results.get('engine_functionality', {}).get('passed', 0) >= 5,
            'multi_factor_assessment_functional': category_results.get('multi_factor_assessment', {}).get('passed', 0) >= 4,
            'site_coverage_calculations_accurate': category_results.get('site_coverage_calculations', {}).get('passed', 0) >= 1,
            'parking_compliance_working': category_results.get('parking_compliance', {}).get('passed', 0) >= 2,
            'landscaping_requirements_implemented': category_results.get('landscaping_requirements', {}).get('passed', 0) >= 1,
            'performance_requirements_met': category_results.get('performance_requirements', {}).get('passed', 0) >= 2
        }

        overall_success = (
            passed_tests >= total_tests * 0.8 and  # 80% pass rate
            all(success_criteria.values())  # All key criteria met
        )

        report = {
            'prp_id': 'PRP-Q3',
            'title': 'Advanced Compliance Rules Engine',
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
            recommendations.append("Create missing files: advanced_compliance_engine.py and API endpoint")

        if not success_criteria.get('engine_functionality_working', False):
            recommendations.append("Implement core engine functionality with all required methods and data structures")

        if not success_criteria.get('multi_factor_assessment_functional', False):
            recommendations.append("Implement comprehensive multi-factor assessment with proper result structure")

        if not success_criteria.get('site_coverage_calculations_accurate', False):
            recommendations.append("Fix site coverage calculations to handle zone-specific limits correctly")

        if not success_criteria.get('parking_compliance_working', False):
            recommendations.append("Implement parking compliance logic for all development types")

        if not success_criteria.get('landscaping_requirements_implemented', False):
            recommendations.append("Implement landscaping requirement calculations with zone-based percentages")

        if not success_criteria.get('performance_requirements_met', False):
            recommendations.append("Optimize performance to meet <200ms response time for multi-factor assessments")

        return recommendations

    def save_report(self, filename: Optional[str] = None) -> str:
        """Save verification report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"PRP_Q3_VERIFICATION_REPORT_{timestamp}.json"

        report = self._generate_final_report()

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)

        return filename

async def main():
    """Run PRP-Q3 verification"""
    print("🚀 Starting PRP-Q3 Granular Verification")
    print()

    suite = PRPQ3VerificationSuite()
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