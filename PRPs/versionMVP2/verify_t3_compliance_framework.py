#!/usr/bin/env python3
"""
TOD Compliance Framework Verification Script
Tests PRP-T3 implementation with rule engine and framework verification
"""

import sys
import os
import requests
import json
import time
from typing import Dict, List, Any, Tuple

# Test scenarios for TOD compliance assessment
TOD_TEST_SCENARIOS = [
    {
        "name": "Premium TOD - Multi Dwelling",
        "zone": "R4",
        "development_type": "multi_dwelling_housing",
        "unit_count": 20,
        "transport_access": "premium",
        "gfa": 1500,
        "site_area": 800,
        "expected_outcomes": {
            "parking_reduction": 40,
            "density_bonus": 50,
            "height_variation": True,
            "design_excellence": False
        }
    },
    {
        "name": "High TOD - Residential Flat Building",
        "zone": "R3",
        "development_type": "residential_flat_building",
        "unit_count": 45,
        "transport_access": "high",
        "gfa": 3200,
        "site_area": 1200,
        "expected_outcomes": {
            "parking_reduction": 30,
            "density_bonus": 40,
            "height_variation": True,
            "design_excellence": True
        }
    },
    {
        "name": "Medium TOD - Mixed Use",
        "zone": "B2",
        "development_type": "mixed_use",
        "unit_count": 12,
        "transport_access": "medium",
        "gfa": 2100,
        "site_area": 600,
        "expected_outcomes": {
            "parking_reduction": 20,
            "density_bonus": 30,
            "height_variation": False,
            "design_excellence": False
        }
    }
]

DEVELOPMENT_TYPE_TESTS = [
    "dwelling_house",
    "dual_occupancy",
    "multi_dwelling_housing",
    "residential_flat_building",
    "commercial_premises",
    "mixed_use"
]

BASE_URL = "http://localhost:3007"

class TODComplianceFrameworkVerifier:
    def __init__(self):
        self.results = {
            "rule_engine_accuracy": {"passed": 0, "failed": 0, "tests": []},
            "development_type_intelligence": {"passed": 0, "failed": 0, "tests": []},
            "compliance_assessment": {"passed": 0, "failed": 0, "tests": []},
            "framework_integration": {"passed": 0, "failed": 0, "tests": []}
        }

    def verify_compliance_engine_exists(self) -> bool:
        """Verify TOD compliance engine files exist"""
        try:
            required_files = [
                "services/tod_compliance_checker.py",
                "services/tod_rules_engine.py"
            ]

            files_exist = all(os.path.exists(file_path) for file_path in required_files)

            if files_exist:
                # Check for key components in compliance checker
                with open("services/tod_compliance_checker.py", 'r') as f:
                    content = f.read()
                    required_elements = [
                        "TODComplianceChecker",
                        "assess_compliance",
                        "calculate_density_bonus",
                        "check_parking_reduction"
                    ]
                    return all(element in content for element in required_elements)

            return False
        except Exception as e:
            print(f"Error checking compliance engine: {e}")
            return False

    def test_tod_rule_engine_accuracy(self, scenario: Dict) -> Dict[str, Any]:
        """Test TOD rule engine accuracy for compliance scenarios"""
        test_result = {
            "test_name": f"Rule engine for {scenario['name']}",
            "scenario": scenario['name'],
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Call TOD compliance assessment API
            payload = {
                "zone": scenario['zone'],
                "development_type": scenario['development_type'],
                "unit_count": scenario['unit_count'],
                "transport_access": scenario['transport_access'],
                "gfa": scenario['gfa'],
                "site_area": scenario['site_area']
            }

            response = requests.post(
                f"{BASE_URL}/api/tod/compliance-assessment",
                json=payload,
                timeout=10
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify compliance assessment components
                required_components = [
                    "parking_assessment",
                    "density_assessment",
                    "height_assessment",
                    "design_requirements",
                    "overall_compliance"
                ]

                has_all_components = all(comp in data for comp in required_components)

                # Check accuracy of specific calculations
                parking_accurate = self._check_parking_accuracy(data, scenario)
                density_accurate = self._check_density_accuracy(data, scenario)
                height_accurate = self._check_height_accuracy(data, scenario)

                test_result["passed"] = has_all_components and parking_accurate and density_accurate
                test_result["details"] = {
                    "has_all_components": has_all_components,
                    "parking_accurate": parking_accurate,
                    "density_accurate": density_accurate,
                    "height_accurate": height_accurate,
                    "api_response": data
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def _check_parking_accuracy(self, data: Dict, scenario: Dict) -> bool:
        """Check parking reduction calculation accuracy"""
        try:
            parking_data = data.get('parking_assessment', {})
            calculated_reduction = parking_data.get('reduction_percentage', 0)
            expected_range = scenario['expected_outcomes']['parking_reduction']

            # Allow ±5% tolerance
            return abs(calculated_reduction - expected_range) <= 5
        except:
            return False

    def _check_density_accuracy(self, data: Dict, scenario: Dict) -> bool:
        """Check density bonus calculation accuracy"""
        try:
            density_data = data.get('density_assessment', {})
            calculated_bonus = density_data.get('bonus_percentage', 0)
            expected_range = scenario['expected_outcomes']['density_bonus']

            # Allow ±10% tolerance
            return abs(calculated_bonus - expected_range) <= 10
        except:
            return False

    def _check_height_accuracy(self, data: Dict, scenario: Dict) -> bool:
        """Check height variation assessment accuracy"""
        try:
            height_data = data.get('height_assessment', {})
            has_variation = height_data.get('variation_available', False)
            expected_variation = scenario['expected_outcomes']['height_variation']

            return has_variation == expected_variation
        except:
            return False

    def test_development_type_autocomplete(self, dev_type: str) -> Dict[str, Any]:
        """Test development type autocomplete and intelligence"""
        test_result = {
            "test_name": f"Development type autocomplete for {dev_type}",
            "development_type": dev_type,
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Test development type selector API
            response = requests.get(
                f"{BASE_URL}/api/tod/development-types",
                params={
                    "zone": "R3",
                    "transport_access": "high",
                    "query": dev_type[:4]  # Partial query for autocomplete
                },
                timeout=3
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify autocomplete features
                has_suggestions = len(data.get('development_types', [])) > 0
                fast_response = test_result["response_time"] < 0.5
                relevant_match = any(
                    dev_type in dt.get('id', '')
                    for dt in data.get('development_types', [])
                )

                # Check TOD eligibility information
                has_tod_info = any(
                    'tod_eligible' in dt and 'tod_benefits' in dt
                    for dt in data.get('development_types', [])
                )

                test_result["passed"] = has_suggestions and fast_response and relevant_match and has_tod_info
                test_result["details"] = {
                    "has_suggestions": has_suggestions,
                    "fast_response": fast_response,
                    "relevant_match": relevant_match,
                    "has_tod_info": has_tod_info,
                    "suggestion_count": len(data.get('development_types', [])),
                    "suggestions": data.get('development_types', [])[:3]
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_comprehensive_compliance_assessment(self) -> Dict[str, Any]:
        """Test comprehensive compliance assessment workflow"""
        test_result = {
            "test_name": "Comprehensive compliance assessment",
            "passed": False,
            "details": {}
        }

        try:
            # Test complete workflow with complex scenario
            complex_scenario = {
                "address": "10 Railway Street, Chatswood NSW 2067",
                "zone": "R4",
                "development_type": "residential_flat_building",
                "unit_count": 50,
                "gfa": 4000,
                "site_area": 1500,
                "special_requirements": {
                    "affordable_housing": True,
                    "design_excellence": True,
                    "green_building": True
                }
            }

            start_time = time.time()

            response = requests.post(
                f"{BASE_URL}/api/tod/comprehensive-assessment",
                json=complex_scenario,
                timeout=15
            )

            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify comprehensive assessment components
                required_sections = [
                    "property_analysis",
                    "transport_assessment",
                    "compliance_matrix",
                    "recommendations",
                    "report_summary"
                ]

                has_all_sections = all(section in data for section in required_sections)

                # Check assessment quality
                has_calculations = 'calculations' in data.get('compliance_matrix', {})
                has_recommendations = len(data.get('recommendations', [])) > 0
                reasonable_time = response_time < 5.0

                test_result["passed"] = has_all_sections and has_calculations and has_recommendations and reasonable_time
                test_result["details"] = {
                    "has_all_sections": has_all_sections,
                    "has_calculations": has_calculations,
                    "has_recommendations": has_recommendations,
                    "reasonable_time": reasonable_time,
                    "response_time": response_time,
                    "assessment_summary": data.get('report_summary', {})
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_ui_component_integration(self) -> Dict[str, Any]:
        """Test TOD UI component integration"""
        test_result = {
            "test_name": "TOD UI component integration",
            "passed": False,
            "details": {}
        }

        try:
            # Check TOD component files
            tod_components = [
                "frontend-nextjs/components/tod/TODDevelopmentTypeSelector.tsx",
                "frontend-nextjs/components/tod/TODComplianceDashboard.tsx"
            ]

            components_exist = {}
            for component in tod_components:
                components_exist[component] = os.path.exists(component)

            # Check integration in main page
            main_page = "frontend-nextjs/app/authoritative/page.tsx"
            if os.path.exists(main_page):
                with open(main_page, 'r') as f:
                    content = f.read()
                    has_tod_integration = any(
                        comp_name in content
                        for comp_name in ['TODDevelopmentTypeSelector', 'TODComplianceDashboard', 'TODParkingCalculator']
                    )
            else:
                has_tod_integration = False

            all_components_exist = all(components_exist.values())

            test_result["passed"] = all_components_exist and has_tod_integration
            test_result["details"] = {
                "components_exist": components_exist,
                "all_components_exist": all_components_exist,
                "has_tod_integration": has_tod_integration,
                "main_page_exists": os.path.exists(main_page)
            }

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_sepp_housing_compliance(self) -> Dict[str, Any]:
        """Test SEPP (Housing) 2021 compliance interpretation"""
        test_result = {
            "test_name": "SEPP (Housing) 2021 compliance",
            "passed": False,
            "details": {}
        }

        try:
            # Test specific SEPP Housing provisions
            sepp_test_data = {
                "zone": "R3",
                "development_type": "multi_dwelling_housing",
                "site_area": 600,
                "transport_distance": 300,
                "transport_type": "heavy_rail"
            }

            response = requests.post(
                f"{BASE_URL}/api/tod/sepp-housing-check",
                json=sepp_test_data,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                # Verify SEPP Housing specific checks
                required_checks = [
                    "minimum_site_area_check",
                    "transport_accessibility_check",
                    "density_controls_check",
                    "design_quality_check"
                ]

                has_all_checks = all(check in data for check in required_checks)

                # Verify compliance with known SEPP Housing rules
                correct_transport_check = data.get('transport_accessibility_check', {}).get('compliant', False)
                has_provisions = len(data.get('applicable_provisions', [])) > 0

                test_result["passed"] = has_all_checks and correct_transport_check and has_provisions
                test_result["details"] = {
                    "has_all_checks": has_all_checks,
                    "correct_transport_check": correct_transport_check,
                    "has_provisions": has_provisions,
                    "sepp_response": data
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def run_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        print("🚀 Starting TOD Compliance Framework Verification...")

        # Test 1: Compliance engine existence
        print("\n📁 Checking compliance engine files...")
        engine_exists = self.verify_compliance_engine_exists()
        if engine_exists:
            print("✅ TOD compliance engine found")
        else:
            print("❌ TOD compliance engine missing")

        # Test 2: Rule engine accuracy
        print("\n⚖️ Testing rule engine accuracy...")
        for scenario in TOD_TEST_SCENARIOS:
            result = self.test_tod_rule_engine_accuracy(scenario)
            self.results["rule_engine_accuracy"]["tests"].append(result)

            if result["passed"]:
                self.results["rule_engine_accuracy"]["passed"] += 1
                print(f"✅ {result['test_name']} - {result['response_time']:.3f}s")
            else:
                self.results["rule_engine_accuracy"]["failed"] += 1
                print(f"❌ {result['test_name']} - {result.get('details', {}).get('error', 'Rule engine failed')}")

        # Test 3: Development type intelligence
        print("\n🏗️ Testing development type autocomplete...")
        for dev_type in DEVELOPMENT_TYPE_TESTS:
            result = self.test_development_type_autocomplete(dev_type)
            self.results["development_type_intelligence"]["tests"].append(result)

            if result["passed"]:
                self.results["development_type_intelligence"]["passed"] += 1
                print(f"✅ Dev type '{dev_type}' - {result['response_time']:.3f}s")
            else:
                self.results["development_type_intelligence"]["failed"] += 1
                print(f"❌ Dev type '{dev_type}' - Autocomplete issues")

        # Test 4: Comprehensive assessment
        print("\n📋 Testing comprehensive compliance assessment...")
        comprehensive_result = self.test_comprehensive_compliance_assessment()
        self.results["compliance_assessment"]["tests"].append(comprehensive_result)

        if comprehensive_result["passed"]:
            self.results["compliance_assessment"]["passed"] += 1
            print("✅ Comprehensive assessment working")
        else:
            self.results["compliance_assessment"]["failed"] += 1
            print("❌ Comprehensive assessment failed")

        # Test 5: UI integration
        print("\n🎨 Testing UI component integration...")
        ui_result = self.test_ui_component_integration()
        self.results["framework_integration"]["tests"].append(ui_result)

        if ui_result["passed"]:
            self.results["framework_integration"]["passed"] += 1
            print("✅ UI components properly integrated")
        else:
            self.results["framework_integration"]["failed"] += 1
            print("❌ UI integration incomplete")

        # Test 6: SEPP Housing compliance
        print("\n🏛️ Testing SEPP (Housing) 2021 compliance...")
        sepp_result = self.test_sepp_housing_compliance()
        self.results["framework_integration"]["tests"].append(sepp_result)

        if sepp_result["passed"]:
            self.results["framework_integration"]["passed"] += 1
            print("✅ SEPP Housing compliance working")
        else:
            self.results["framework_integration"]["failed"] += 1
            print("❌ SEPP Housing compliance issues")

        return self.results

    def generate_report(self) -> Dict[str, Any]:
        """Generate verification report"""
        total_tests = sum(
            len(category["tests"])
            for category in self.results.values()
        )
        total_passed = sum(
            category["passed"]
            for category in self.results.values()
        )

        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        report = {
            "prp_id": "PRP-T3",
            "component": "TOD Compliance Framework",
            "verification_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total_tests,
            "tests_passed": total_passed,
            "success_rate": round(success_rate, 1),
            "status": "PASS" if success_rate >= 80 else "FAIL",
            "category_results": self.results,
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        if self.results["rule_engine_accuracy"]["failed"] > 0:
            recommendations.append("Review TOD rule engine calculation accuracy")
            recommendations.append("Validate SEPP (Housing) 2021 rule interpretations")

        if self.results["development_type_intelligence"]["failed"] > 0:
            recommendations.append("Improve development type autocomplete performance")
            recommendations.append("Add better TOD eligibility indicators")

        if self.results["compliance_assessment"]["failed"] > 0:
            recommendations.append("Optimize comprehensive assessment workflow")
            recommendations.append("Improve assessment response times")

        if self.results["framework_integration"]["failed"] > 0:
            recommendations.append("Complete TOD UI component integration")
            recommendations.append("Finalize SEPP Housing compliance checks")

        if not recommendations:
            recommendations.append("TOD compliance framework meets all criteria")

        return recommendations

def main():
    verifier = TODComplianceFrameworkVerifier()

    # Run verification
    results = verifier.run_verification()

    # Generate report
    report = verifier.generate_report()

    # Print summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print(f"Status: {report['status']}")
    print(f"Success Rate: {report['success_rate']}%")
    print(f"Tests Passed: {report['tests_passed']}/{report['total_tests']}")

    # Save detailed results
    with open('PRPs/versionMVP2/verify_t3_results.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed results saved to verify_t3_results.json")

    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'PASS' else 1)

if __name__ == "__main__":
    main()