#!/usr/bin/env python3
"""
Transport Proximity Detection Verification Script
Tests PRP-T2 implementation with autocomplete and caching verification
"""

import sys
import os
import requests
import json
import time
from typing import Dict, List, Any
import sqlite3
import psycopg2
from concurrent.futures import ThreadPoolExecutor

# Test coordinates for various transport hubs
TEST_LOCATIONS = [
    {
        "name": "Chatswood Station",
        "lat": -33.7969,
        "lng": 151.1846,
        "expected_transport": ["heavy_rail", "bus"],
        "expected_distance": 100
    },
    {
        "name": "Circular Quay",
        "lat": -33.8616,
        "lng": 151.2111,
        "expected_transport": ["heavy_rail", "ferry", "bus"],
        "expected_distance": 50
    },
    {
        "name": "Burwood Station",
        "lat": -33.8777,
        "lng": 151.1044,
        "expected_transport": ["heavy_rail", "light_rail", "bus"],
        "expected_distance": 75
    },
    {
        "name": "Surry Hills",
        "lat": -33.8886,
        "lng": 151.2094,
        "expected_transport": ["light_rail", "bus"],
        "expected_distance": 200
    }
]

AUTOCOMPLETE_QUERIES = [
    "train",
    "station",
    "bus",
    "light rail",
    "tram",
    "ferry",
    "metro"
]

BASE_URL = "http://localhost:3007"

class TransportDetectionVerifier:
    def __init__(self):
        self.results = {
            "detection_accuracy": {"passed": 0, "failed": 0, "tests": []},
            "autocomplete_performance": {"passed": 0, "failed": 0, "tests": []},
            "caching_efficiency": {"passed": 0, "failed": 0, "tests": []},
            "data_quality": {"passed": 0, "failed": 0, "tests": []}
        }

    def verify_transport_detector_exists(self) -> bool:
        """Verify transport proximity detector service exists"""
        try:
            detector_path = "services/transport_proximity_detector.py"
            if os.path.exists(detector_path):
                with open(detector_path, 'r') as f:
                    content = f.read()
                    # Check for key detector features
                    required_elements = [
                        "TransportProximityDetector",
                        "detect_nearby_transport",
                        "calculate_distance",
                        "get_service_frequency"
                    ]
                    return all(element in content for element in required_elements)
            return False
        except Exception as e:
            print(f"Error checking detector: {e}")
            return False

    def test_transport_detection_accuracy(self, location: Dict) -> Dict[str, Any]:
        """Test transport detection accuracy for given location"""
        test_result = {
            "test_name": f"Transport detection for {location['name']}",
            "location": location['name'],
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Call transport detection API
            response = requests.get(
                f"{BASE_URL}/api/tod/transport-proximity",
                params={
                    "lat": location['lat'],
                    "lng": location['lng'],
                    "radius": 1000
                },
                timeout=10
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Verify detection results
                transport_found = len(data.get('transport_services', [])) > 0
                expected_types_found = any(
                    service.get('type') in location['expected_transport']
                    for service in data.get('transport_services', [])
                )

                # Check accuracy of closest transport
                closest_service = min(
                    data.get('transport_services', []),
                    key=lambda x: x.get('distance', float('inf')),
                    default={}
                )

                distance_accurate = (
                    closest_service and
                    abs(closest_service.get('distance', 0) - location['expected_distance']) < 200
                )

                test_result["passed"] = transport_found and expected_types_found and distance_accurate
                test_result["details"] = {
                    "transport_found": transport_found,
                    "expected_types_found": expected_types_found,
                    "distance_accurate": distance_accurate,
                    "services_count": len(data.get('transport_services', [])),
                    "closest_distance": closest_service.get('distance'),
                    "api_response": data
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_autocomplete_performance(self, query: str) -> Dict[str, Any]:
        """Test autocomplete performance for transport search"""
        test_result = {
            "test_name": f"Autocomplete for '{query}'",
            "query": query,
            "passed": False,
            "details": {},
            "response_time": 0
        }

        try:
            start_time = time.time()

            # Test autocomplete endpoint
            response = requests.get(
                f"{BASE_URL}/api/tod/transport-autocomplete",
                params={
                    "query": query,
                    "lat": -33.8688,  # Sydney CBD
                    "lng": 151.2093,
                    "limit": 10
                },
                timeout=2
            )

            test_result["response_time"] = time.time() - start_time

            if response.status_code == 200:
                data = response.json()

                # Performance criteria
                fast_response = test_result["response_time"] < 0.3
                has_results = len(data.get('suggestions', [])) > 0
                relevant_results = any(
                    query.lower() in suggestion.get('name', '').lower()
                    for suggestion in data.get('suggestions', [])
                )

                # Check result quality
                has_metadata = all(
                    all(key in suggestion for key in ['name', 'type', 'distance'])
                    for suggestion in data.get('suggestions', [])
                )

                test_result["passed"] = fast_response and has_results and relevant_results and has_metadata
                test_result["details"] = {
                    "fast_response": fast_response,
                    "has_results": has_results,
                    "relevant_results": relevant_results,
                    "has_metadata": has_metadata,
                    "result_count": len(data.get('suggestions', [])),
                    "top_results": data.get('suggestions', [])[:3]
                }
            else:
                test_result["details"]["error"] = f"API error: {response.status_code}"

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_caching_efficiency(self) -> Dict[str, Any]:
        """Test caching system efficiency"""
        test_result = {
            "test_name": "Transport data caching efficiency",
            "passed": False,
            "details": {},
            "cache_performance": {}
        }

        try:
            # Test same location multiple times to check caching
            test_location = TEST_LOCATIONS[0]

            # First request (should populate cache)
            start_time = time.time()
            first_response = requests.get(
                f"{BASE_URL}/api/tod/transport-proximity",
                params={
                    "lat": test_location['lat'],
                    "lng": test_location['lng'],
                    "radius": 1000
                },
                timeout=10
            )
            first_time = time.time() - start_time

            # Second request (should use cache)
            start_time = time.time()
            second_response = requests.get(
                f"{BASE_URL}/api/tod/transport-proximity",
                params={
                    "lat": test_location['lat'],
                    "lng": test_location['lng'],
                    "radius": 1000
                },
                timeout=10
            )
            second_time = time.time() - start_time

            if first_response.status_code == 200 and second_response.status_code == 200:
                # Cache efficiency check
                cache_faster = second_time < first_time * 0.8  # 20% improvement expected
                consistent_results = (
                    first_response.json().get('transport_services') ==
                    second_response.json().get('transport_services')
                )

                test_result["passed"] = cache_faster and consistent_results
                test_result["details"] = {
                    "cache_faster": cache_faster,
                    "consistent_results": consistent_results,
                    "first_response_time": first_time,
                    "second_response_time": second_time,
                    "improvement_ratio": first_time / second_time if second_time > 0 else 0
                }

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test system performance under concurrent load"""
        test_result = {
            "test_name": "Concurrent request handling",
            "passed": False,
            "details": {}
        }

        def make_request(location):
            try:
                start_time = time.time()
                response = requests.get(
                    f"{BASE_URL}/api/tod/transport-proximity",
                    params={
                        "lat": location['lat'],
                        "lng": location['lng'],
                        "radius": 1000
                    },
                    timeout=15
                )
                return {
                    "status": response.status_code,
                    "time": time.time() - start_time,
                    "success": response.status_code == 200
                }
            except Exception as e:
                return {"status": 0, "time": 15, "success": False, "error": str(e)}

        try:
            # Test with 10 concurrent requests
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(make_request, TEST_LOCATIONS[i % len(TEST_LOCATIONS)])
                    for i in range(10)
                ]
                results = [future.result() for future in futures]

            # Analyze results
            successful_requests = sum(1 for r in results if r['success'])
            average_time = sum(r['time'] for r in results) / len(results)
            max_time = max(r['time'] for r in results)

            # Success criteria
            high_success_rate = successful_requests >= 8  # 80% success
            reasonable_performance = average_time < 3.0
            no_timeouts = max_time < 10.0

            test_result["passed"] = high_success_rate and reasonable_performance and no_timeouts
            test_result["details"] = {
                "successful_requests": successful_requests,
                "total_requests": len(results),
                "success_rate": successful_requests / len(results),
                "average_time": average_time,
                "max_time": max_time,
                "all_results": results
            }

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def verify_database_schema(self) -> Dict[str, Any]:
        """Verify transport proximity database schema"""
        test_result = {
            "test_name": "Database schema verification",
            "passed": False,
            "details": {}
        }

        try:
            # Check if schema exists (using db_safety_wrapper)
            sys.path.append('.')
            from db_safety_wrapper import get_safe_connection

            conn = get_safe_connection()
            cursor = conn.cursor()

            # Check for transport_proximity table
            cursor.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'transport_proximity'
            """)
            columns = cursor.fetchall()

            expected_columns = {
                'property_id', 'transport_type', 'stop_name',
                'distance_meters', 'service_frequency', 'confidence_score'
            }
            actual_columns = {row[0] for row in columns}

            schema_complete = expected_columns.issubset(actual_columns)

            test_result["passed"] = schema_complete
            test_result["details"] = {
                "schema_complete": schema_complete,
                "expected_columns": list(expected_columns),
                "actual_columns": list(actual_columns),
                "missing_columns": list(expected_columns - actual_columns)
            }

            cursor.close()
            conn.close()

        except Exception as e:
            test_result["details"]["exception"] = str(e)

        return test_result

    def run_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        print("🚀 Starting Transport Proximity Detection Verification...")

        # Test 1: Detector existence
        print("\n📁 Checking detector service files...")
        detector_exists = self.verify_transport_detector_exists()
        if detector_exists:
            print("✅ Transport proximity detector found")
        else:
            print("❌ Transport proximity detector missing")

        # Test 2: Detection accuracy
        print("\n📍 Testing transport detection accuracy...")
        for location in TEST_LOCATIONS:
            result = self.test_transport_detection_accuracy(location)
            self.results["detection_accuracy"]["tests"].append(result)

            if result["passed"]:
                self.results["detection_accuracy"]["passed"] += 1
                print(f"✅ {result['test_name']} - {result['response_time']:.3f}s")
            else:
                self.results["detection_accuracy"]["failed"] += 1
                print(f"❌ {result['test_name']} - {result.get('details', {}).get('error', 'Detection failed')}")

        # Test 3: Autocomplete performance
        print("\n⚡ Testing autocomplete performance...")
        for query in AUTOCOMPLETE_QUERIES:
            result = self.test_autocomplete_performance(query)
            self.results["autocomplete_performance"]["tests"].append(result)

            if result["passed"]:
                self.results["autocomplete_performance"]["passed"] += 1
                print(f"✅ Autocomplete '{query}' - {result['response_time']:.3f}s")
            else:
                self.results["autocomplete_performance"]["failed"] += 1
                print(f"❌ Autocomplete '{query}' - Too slow or no results")

        # Test 4: Caching efficiency
        print("\n💾 Testing caching efficiency...")
        cache_result = self.test_caching_efficiency()
        self.results["caching_efficiency"]["tests"].append(cache_result)

        if cache_result["passed"]:
            self.results["caching_efficiency"]["passed"] += 1
            print("✅ Caching system working efficiently")
        else:
            self.results["caching_efficiency"]["failed"] += 1
            print("❌ Caching system needs optimization")

        # Test 5: Concurrent handling
        print("\n🔄 Testing concurrent request handling...")
        concurrent_result = self.test_concurrent_requests()
        self.results["data_quality"]["tests"].append(concurrent_result)

        if concurrent_result["passed"]:
            self.results["data_quality"]["passed"] += 1
            print("✅ Concurrent requests handled successfully")
        else:
            self.results["data_quality"]["failed"] += 1
            print("❌ Performance issues under load")

        # Test 6: Database schema
        print("\n🗄️ Verifying database schema...")
        schema_result = self.verify_database_schema()
        self.results["data_quality"]["tests"].append(schema_result)

        if schema_result["passed"]:
            self.results["data_quality"]["passed"] += 1
            print("✅ Database schema properly configured")
        else:
            self.results["data_quality"]["failed"] += 1
            print("❌ Database schema incomplete")

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
            "prp_id": "PRP-T2",
            "component": "Transport Proximity Detection",
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

        if self.results["detection_accuracy"]["failed"] > 0:
            recommendations.append("Improve transport detection accuracy algorithms")
            recommendations.append("Add more comprehensive transport data sources")

        if self.results["autocomplete_performance"]["failed"] > 0:
            recommendations.append("Optimize autocomplete query performance")
            recommendations.append("Implement better result ranking algorithms")

        if self.results["caching_efficiency"]["failed"] > 0:
            recommendations.append("Implement or optimize caching layer")
            recommendations.append("Add cache invalidation strategies")

        if self.results["data_quality"]["failed"] > 0:
            recommendations.append("Improve concurrent request handling")
            recommendations.append("Complete database schema implementation")

        if not recommendations:
            recommendations.append("Transport detection system meets all criteria")

        return recommendations

def main():
    verifier = TransportDetectionVerifier()

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
    with open('PRPs/versionMVP2/verify_t2_results.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Detailed results saved to verify_t2_results.json")

    # Exit with appropriate code
    sys.exit(0 if report['status'] == 'PASS' else 1)

if __name__ == "__main__":
    main()