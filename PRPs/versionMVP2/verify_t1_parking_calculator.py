#!/usr/bin/env python3
"""
TOD Parking Calculator Verification Script
Tests PRP-T1 implementation with autocomplete verification
"""

import sys
import os
import requests
import json
import time
from typing import Dict, List, Any
import pytest

# Test data for verification
TEST_PROPERTIES = [
    {
        "address": "10 Railway Street, Chatswood NSW 2067",
        "expected_transport": "heavy_rail",
        "distance_to_station": 200,
        "development_type": "multi_dwelling_housing",
        "unit_count": 12
    },
    {
        "address": "45 Pacific Highway, North Sydney NSW 2060",
        "expected_transport": "heavy_rail",
        "distance_to_station": 350,
        "development_type": "residential_flat_building",
        "unit_count": 24
    },
    {
        "address": "123 Burwood Road, Burwood NSW 2134",
        "expected_transport": "light_rail",
        "distance_to_station": 150,
        "development_type": "multi_dwelling_housing",
        "unit_count": 8
    }
]

BASE_URL = "http://localhost:3007"

class TODParkingCalculatorVerifier:
    def __init__(self):
        self.results = {
            "calculator_accuracy": {"passed": 0, "failed": 0, "tests": []},
            "transport_detection": {"passed": 0, "failed": 0, "tests": []},
            "ui_responsiveness": {"passed": 0, "failed": 0, "tests": []},
            "autocomplete_functionality": {"passed": 0, "failed": 0, "tests": []}
        }

    def verify_calculator_component_exists(self) -> bool:
        """Verify TODParkingCalculator component exists"""
        try:
            component_path = "frontend-nextjs/components/tod/TODParkingCalculator.tsx"
            if os.path.exists(component_path):
                with open(component_path, 'r') as f:
                    content = f.read()
                    # Check for key component features
                    required_elements = [
                        "TODParkingCalculator",
                        "calculateParkingReduction",
                        "transportProximity",
                        "developmentType",
                        "unitCount"
                    ]
                    return all(element in content for element in required_elements)
            return False
        except Exception as e:
            print(f"Error checking component: {e}")
            return False

    def test_parking_calculation_accuracy(self, property_data: Dict) -> Dict[str, Any]:
        """Test parking calculation accuracy for given property"""
        test_result = {
            "test_name": f"Parking calculation for {property_data['development_type']}",
            "property": property_data['address'],
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Call parking calculation API
            payload = {
                "development_type": property_data['development_type'],
                "unit_count": property_data['unit_count'],
                "transport_proximity": {
                    "type": property_data['expected_transport'],
                    "distance": property_data['distance_to_station']
                }
            }

            response = requests.post(
                f"{BASE_URL}/api/tod/parking-calculator",
                json=payload,
                timeout=5
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify calculation components
                expected_components = [
                    "base_parking_requirement",
                    "reduction_factors",
                    "final_parking_requirement",
                    "reduction_percentage"
                ]

                has_all_components = all(comp in data for comp in expected_components)

                # Verify reduction logic
                reduction_valid = True
                if property_data['distance_to_station'] <= 400:
                    reduction_valid = data.get('reduction_percentage', 0) >= 20
                elif property_data['distance_to_station'] <= 800:
                    reduction_valid = data.get('reduction_percentage', 0) >= 10

                test_result["passed"] = has_all_components and reduction_valid
                test_result["details"] = {
                    "has_all_components": has_all_components,
                    "reduction_valid": reduction_valid,
                    "calculated_reduction": data.get('reduction_percentage', 0),
                    "api_response": data
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_transport_autocomplete(self) -> Dict[str, Any]:
        """Test transport proximity autocomplete functionality"""
        test_result = {
            "test_name": "Transport proximity autocomplete",
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Test autocomplete search
            response = requests.get(
                f"{BASE_URL}/api/tod/transport-autocomplete",
                params={"query": "train", "lat": -33.7969, "lng": 151.1846},
                timeout=3
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify autocomplete features
                has_suggestions = len(data.get('suggestions', [])) > 0
                fast_response = test_result["response_time"] < 0.5
                has_metadata = all(
                    key in data.get('suggestions', [{}])[0]
                    for key in ['name', 'type', 'distance', 'frequency']
                    if data.get('suggestions')
                )

                test_result["passed"] = has_suggestions and fast_response and has_metadata
                test_result["details"] = {
                    "suggestion_count": len(data.get('suggestions', [])),
                    "response_time_ok": fast_response,
                    "has_metadata": has_metadata,
                    "suggestions": data.get('suggestions', [])[:3]  # First 3 for review
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_ui_component_integration(self) -> Dict[str, Any]:
        """Test UI component integration"""
        test_result = {
            "test_name": "UI component integration",
            "passed": False,
            "details": {}
        }

        try:
            # Check if TOD components are properly integrated
            authoritative_page = "frontend-nextjs/app/authoritative/page.tsx"
            if os.path.exists(authoritative_page):
                with open(authoritative_page, 'r') as f:
                    content = f.read()

                    # Check for TOD integration
                    has_tod_import = "TODParkingCalculator" in content or "tod/" in content
                    has_tod_logic = "TOD" in content or "parking" in content.lower()

                    test_result["passed"] = has_tod_import or has_tod_logic
                    test_result["details"] = {
                        "has_tod_import": has_tod_import,
                        "has_tod_logic": has_tod_logic,
                        "file_exists": True
                    }
            else:
                test_result["details"]["file_exists"] = False

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def run_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        print("🚀 Starting TOD Parking Calculator Verification...")

        # Test 1: Component existence
        print("\n📁 Checking component files...")
        component_exists = self.verify_calculator_component_exists()
        if component_exists:
            print("✅ TODParkingCalculator component found")
        else:
            print("❌ TODParkingCalculator component missing")

        # Test 2: Parking calculation accuracy
        print("\n🧮 Testing parking calculation accuracy...")
        for property_data in TEST_PROPERTIES:
            result = self.test_parking_calculation_accuracy(property_data)
            self.results["calculator_accuracy"]["tests"].append(result)

            if result["passed"]:
                self.results["calculator_accuracy"]["passed"] += 1
                print(f"✅ {result['test_name']} - {result['response_time']:.3f}s")
            else:
                self.results["calculator_accuracy"]["failed"] += 1
                print(f"❌ {result['test_name']} - {result.get('details', {}).get('error', 'Unknown error')}")

        # Test 3: Transport autocomplete
        print("\n🚊 Testing transport autocomplete...")
        autocomplete_result = self.test_transport_autocomplete()
        self.results["autocomplete_functionality"]["tests"].append(autocomplete_result)

        if autocomplete_result["passed"]:
            self.results["autocomplete_functionality"]["passed"] += 1
            print(f"✅ Transport autocomplete - {autocomplete_result['response_time']:.3f}s")
        else:
            self.results["autocomplete_functionality"]["failed"] += 1
            print(f"❌ Transport autocomplete - {autocomplete_result.get('details', {}).get('error', 'Failed')}")

        # Test 4: UI integration
        print("\n🎨 Testing UI integration...")
        ui_result = self.test_ui_component_integration()
        self.results["ui_responsiveness"]["tests"].append(ui_result)

        if ui_result["passed"]:
            self.results["ui_responsiveness"]["passed"] += 1
            print("✅ UI integration successful")
        else:
            self.results["ui_responsiveness"]["failed"] += 1
            print("❌ UI integration issues found")

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
            "prp_id": "PRP-T1",
            "component": "TOD Parking Calculator",
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

        # Calculator accuracy recommendations
        if self.results["calculator_accuracy"]["failed"] > 0:
            recommendations.append("Review parking calculation logic for accuracy")
            recommendations.append("Add unit tests for edge cases in parking reductions")

        # Autocomplete recommendations
        if self.results["autocomplete_functionality"]["failed"] > 0:
            recommendations.append("Optimize transport autocomplete response times")
            recommendations.append("Improve autocomplete suggestion relevance")

        # UI recommendations
        if self.results["ui_responsiveness"]["failed"] > 0:
            recommendations.append("Complete TOD component integration in UI")
            recommendations.append("Add proper error handling for TOD features")

        if not recommendations:
            recommendations.append("Implementation meets all verification criteria")

        return recommendations

def main():
    verifier = TODParkingCalculatorVerifier()

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
    with open('PRPs/versionMVP2/verify_t1_results.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed results saved to verify_t1_results.json")

    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'PASS' else 1)

if __name__ == "__main__":
    main()