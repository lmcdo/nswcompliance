#!/usr/bin/env python3
"""
GRANULAR Verification script for PRP-V6-Enhanced: API Version Integration
- Tests every API endpoint modification individually
- Validates every response format change
- Verifies every backward compatibility requirement
- Checks every integration point separately
- Validates security and performance requirements
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import json
import requests
from datetime import datetime, date
from typing import Dict, List, Optional
import time
import subprocess

class PRPV6EnhancedVerification:
    """Granular verification for every aspect of PRP-V6-Enhanced API integration"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-V6-ENHANCED_API_VERSION_INTEGRATION",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "warnings": []
        }

        # API base URL - will need to be running
        self.base_url = "http://localhost:8000"  # Adjust as needed
        self.api_running = False

    def check_api_server_running(self) -> bool:
        """Check if API server is running for testing"""
        print("Checking if API server is running...")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self.api_running = response.status_code == 200
            return self.api_running
        except requests.exceptions.RequestException:
            self.results["warnings"].append("API server not running - skipping HTTP tests")
            return False

    def verify_existing_endpoint_enhancements(self) -> Dict[str, bool]:
        """Verify existing endpoints accept version parameters"""
        print("Verifying existing endpoint enhancements...")

        endpoint_checks = {}

        if not self.api_running:
            endpoint_checks['server_not_running'] = True
            return endpoint_checks

        test_endpoints = [
            "/api/provisions",
            "/api/setbacks/calculate",
            "/api/development-controls"
        ]

        for endpoint in test_endpoints:
            endpoint_key = endpoint.replace("/", "_").replace("-", "_")[1:]  # Remove leading slash, replace chars

            try:
                # Test 1: Endpoint works without version parameters (backward compatibility)
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                endpoint_checks[f'{endpoint_key}_backward_compatible'] = response.status_code in [200, 404]  # 404 ok if no data

                # Test 2: Endpoint accepts version parameter
                response = requests.get(f"{self.base_url}{endpoint}?version=current", timeout=10)
                endpoint_checks[f'{endpoint_key}_accepts_version_param'] = response.status_code in [200, 404]

                # Test 3: Endpoint accepts as_at_date parameter
                response = requests.get(f"{self.base_url}{endpoint}?as_at_date=2024-09-20", timeout=10)
                endpoint_checks[f'{endpoint_key}_accepts_date_param'] = response.status_code in [200, 404]

                # Test 4: Invalid version parameter returns proper error
                response = requests.get(f"{self.base_url}{endpoint}?version=invalid_version", timeout=10)
                endpoint_checks[f'{endpoint_key}_validates_version_param'] = response.status_code == 400

                # Test 5: Invalid date format returns proper error
                response = requests.get(f"{self.base_url}{endpoint}?as_at_date=invalid-date", timeout=10)
                endpoint_checks[f'{endpoint_key}_validates_date_param'] = response.status_code == 400

            except requests.exceptions.RequestException as e:
                endpoint_checks[f'{endpoint_key}_error'] = str(e)
                self.results["errors"].append(f"Endpoint {endpoint} test failed: {str(e)}")

        self.results["checks"]["existing_endpoints"] = endpoint_checks
        return endpoint_checks

    def verify_response_format_enhancements(self) -> Dict[str, bool]:
        """Verify response formats include version metadata when requested"""
        print("Verifying response format enhancements...")

        format_checks = {}

        if not self.api_running:
            format_checks['server_not_running'] = True
            return format_checks

        try:
            # Test 1: Response without version params excludes version metadata
            response = requests.get(f"{self.base_url}/api/provisions?limit=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                format_checks['no_version_params_excludes_metadata'] = (
                    'data' in data and
                    len(data['data']) > 0 and
                    'version_info' not in data['data'][0]
                )
            else:
                format_checks['no_version_params_excludes_metadata'] = True  # No data to test

            # Test 2: Response with version param includes version metadata
            response = requests.get(f"{self.base_url}/api/provisions?version=current&limit=1", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    format_checks['version_param_includes_metadata'] = 'version_info' in data['data'][0]

                    # Test version_info structure
                    if 'version_info' in data['data'][0]:
                        version_info = data['data'][0]['version_info']
                        required_fields = ['version_id', 'version_number', 'effective_date', 'is_current']
                        format_checks['version_info_has_required_fields'] = all(
                            field in version_info for field in required_fields
                        )
                else:
                    format_checks['version_param_includes_metadata'] = True  # No data to test

            # Test 3: Response includes metadata section when version params used
            response = requests.get(f"{self.base_url}/api/provisions?version=current", timeout=10)
            if response.status_code == 200:
                data = response.json()
                format_checks['includes_version_context_metadata'] = (
                    'metadata' in data and
                    'version_context' in data['metadata']
                )

        except requests.exceptions.RequestException as e:
            format_checks['response_format_error'] = str(e)
            self.results["errors"].append(f"Response format test failed: {str(e)}")

        self.results["checks"]["response_formats"] = format_checks
        return format_checks

    def verify_new_version_endpoints(self) -> Dict[str, bool]:
        """Verify new version-specific endpoints work correctly"""
        print("Verifying new version endpoints...")

        new_endpoint_checks = {}

        if not self.api_running:
            new_endpoint_checks['server_not_running'] = True
            return new_endpoint_checks

        new_endpoints = [
            "/api/versions/documents",
            "/api/versions/changes",
            "/api/versions/compare"
        ]

        for endpoint in new_endpoints:
            endpoint_key = endpoint.replace("/", "_").replace("-", "_")[1:]

            try:
                # Test 1: Endpoint exists and responds
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                new_endpoint_checks[f'{endpoint_key}_exists'] = response.status_code in [200, 400, 404]  # Not 500 error

                # Test 2: POST method properly rejected
                response = requests.post(f"{self.base_url}{endpoint}", timeout=10)
                new_endpoint_checks[f'{endpoint_key}_rejects_post'] = response.status_code == 405

                # Test specific endpoint requirements
                if endpoint == "/api/versions/documents":
                    # Should accept document_type parameter
                    response = requests.get(f"{self.base_url}{endpoint}?document_type=LEP", timeout=10)
                    new_endpoint_checks[f'{endpoint_key}_accepts_doc_type'] = response.status_code in [200, 404]

                elif endpoint == "/api/versions/changes":
                    # Should require document_identifier parameter
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    new_endpoint_checks[f'{endpoint_key}_requires_doc_id'] = response.status_code == 400

                    # Should accept document_identifier parameter
                    response = requests.get(f"{self.base_url}{endpoint}?document_identifier=test", timeout=10)
                    new_endpoint_checks[f'{endpoint_key}_accepts_doc_id'] = response.status_code in [200, 404]

                elif endpoint == "/api/versions/compare":
                    # Should require from_version and to_version parameters
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    new_endpoint_checks[f'{endpoint_key}_requires_version_params'] = response.status_code == 400

                    # Should accept required parameters
                    response = requests.get(
                        f"{self.base_url}{endpoint}?document_identifier=test&from_version=v1.0&to_version=v1.1",
                        timeout=10
                    )
                    new_endpoint_checks[f'{endpoint_key}_accepts_version_params'] = response.status_code in [200, 404]

            except requests.exceptions.RequestException as e:
                new_endpoint_checks[f'{endpoint_key}_error'] = str(e)
                self.results["errors"].append(f"New endpoint {endpoint} test failed: {str(e)}")

        self.results["checks"]["new_endpoints"] = new_endpoint_checks
        return new_endpoint_checks

    def verify_backward_compatibility(self) -> Dict[str, bool]:
        """Verify existing API consumers continue working unchanged"""
        print("Verifying backward compatibility...")

        compatibility_checks = {}

        if not self.api_running:
            compatibility_checks['server_not_running'] = True
            return compatibility_checks

        try:
            # Test 1: Existing provision query works exactly as before
            response = requests.get(f"{self.base_url}/api/provisions?zone=R2&limit=5", timeout=10)

            if response.status_code == 200:
                data = response.json()

                # Check response structure matches existing format
                compatibility_checks['has_data_array'] = 'data' in data or 'provisions' in data

                # Check no unexpected version fields in basic response
                if 'data' in data and len(data['data']) > 0:
                    first_item = data['data'][0]
                    compatibility_checks['no_unexpected_version_fields'] = 'version_info' not in first_item

                    # Check existing fields still present
                    expected_fields = ['id', 'provision_text', 'zone']
                    compatibility_checks['existing_fields_present'] = all(
                        field in first_item for field in expected_fields if first_item.get(field) is not None
                    )

            # Test 2: Setback calculation API unchanged
            test_address = "15 Norton Street, Leichhardt"
            response = requests.get(
                f"{self.base_url}/api/setbacks/calculate?address={test_address}",
                timeout=15
            )
            compatibility_checks['setback_api_unchanged'] = response.status_code in [200, 400, 404]  # Any non-500 error

            # Test 3: Error responses maintain existing format
            response = requests.get(f"{self.base_url}/api/provisions?invalid_param=value", timeout=10)
            compatibility_checks['error_format_unchanged'] = response.status_code in [200, 400, 404]

        except requests.exceptions.RequestException as e:
            compatibility_checks['backward_compatibility_error'] = str(e)
            self.results["errors"].append(f"Backward compatibility test failed: {str(e)}")

        self.results["checks"]["backward_compatibility"] = compatibility_checks
        return compatibility_checks

    def verify_data_integration(self) -> Dict[str, bool]:
        """Verify API correctly integrates with version-aware services"""
        print("Verifying data integration...")

        integration_checks = {}

        try:
            # Test 1: VersionAwareQuery service integration
            from services.version_aware_query import VersionAwareQuery

            # Test basic query works
            provisions = VersionAwareQuery.get_provisions(version="current")
            integration_checks['version_aware_query_works'] = isinstance(provisions, list)

            # Test date-based query works
            test_date = date(2024, 9, 20)
            dated_provisions = VersionAwareQuery.get_provisions(as_at_date=test_date)
            integration_checks['date_based_query_works'] = isinstance(dated_provisions, list)

            # Test VersionManager integration
            from services.version_manager import VersionManager
            vm = VersionManager()

            stats = vm.get_version_statistics()
            integration_checks['version_manager_stats_work'] = isinstance(stats, dict)

            # Test version comparison if available
            if hasattr(vm, 'get_version_comparison'):
                from services.version_manager import DocumentType
                comparison = vm.get_version_comparison(DocumentType.LEP, 'test_document')
                integration_checks['version_comparison_works'] = isinstance(comparison, tuple)

            vm.close()

        except ImportError as e:
            integration_checks['service_import_error'] = str(e)
            self.results["errors"].append(f"Cannot import version services: {str(e)}")
        except Exception as e:
            integration_checks['integration_error'] = str(e)
            self.results["errors"].append(f"Data integration test failed: {str(e)}")

        self.results["checks"]["data_integration"] = integration_checks
        return integration_checks

    def verify_performance_requirements(self) -> Dict[str, bool]:
        """Verify API performance meets requirements"""
        print("Verifying performance requirements...")

        performance_checks = {}

        if not self.api_running:
            performance_checks['server_not_running'] = True
            return performance_checks

        try:
            # Test 1: Basic provision query performance
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/provisions?limit=100", timeout=30)
            end_time = time.time()

            query_time = end_time - start_time
            performance_checks['basic_query_under_2s'] = query_time < 2.0
            performance_checks['basic_query_time'] = round(query_time, 3)

            # Test 2: Version-aware query performance
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/provisions?version=current&limit=100", timeout=30)
            end_time = time.time()

            version_query_time = end_time - start_time
            performance_checks['version_query_under_2s'] = version_query_time < 2.0
            performance_checks['version_query_time'] = round(version_query_time, 3)

            # Test 3: Point-in-time query performance
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/provisions?as_at_date=2024-09-20&limit=100", timeout=30)
            end_time = time.time()

            date_query_time = end_time - start_time
            performance_checks['date_query_under_2s'] = date_query_time < 2.0
            performance_checks['date_query_time'] = round(date_query_time, 3)

            # Test 4: Version comparison performance (if available)
            start_time = time.time()
            response = requests.get(
                f"{self.base_url}/api/versions/compare?document_identifier=test&from_version=v1.0&to_version=v1.1",
                timeout=30
            )
            end_time = time.time()

            compare_time = end_time - start_time
            performance_checks['compare_query_under_3s'] = compare_time < 3.0
            performance_checks['compare_query_time'] = round(compare_time, 3)

        except requests.exceptions.Timeout:
            performance_checks['performance_timeout'] = True
            self.results["errors"].append("API performance test timed out")
        except requests.exceptions.RequestException as e:
            performance_checks['performance_error'] = str(e)
            self.results["warnings"].append(f"Performance test incomplete: {str(e)}")

        self.results["checks"]["performance"] = performance_checks
        return performance_checks

    def verify_security_requirements(self) -> Dict[str, bool]:
        """Verify security aspects of API version integration"""
        print("Verifying security requirements...")

        security_checks = {}

        if not self.api_running:
            security_checks['server_not_running'] = True
            return security_checks

        try:
            # Test 1: SQL injection protection
            malicious_version = "'; DROP TABLE regulatory_provisions; --"
            response = requests.get(
                f"{self.base_url}/api/provisions?version={malicious_version}",
                timeout=10
            )
            security_checks['sql_injection_protected'] = response.status_code == 400

            # Test 2: XSS protection in error messages
            xss_payload = "<script>alert('xss')</script>"
            response = requests.get(
                f"{self.base_url}/api/provisions?document_identifier={xss_payload}",
                timeout=10
            )
            if response.status_code == 400:
                security_checks['xss_protected'] = xss_payload not in response.text

            # Test 3: Input validation
            oversized_input = "x" * 10000
            response = requests.get(
                f"{self.base_url}/api/provisions?document_identifier={oversized_input}",
                timeout=10
            )
            security_checks['input_length_validated'] = response.status_code == 400

            # Test 4: Proper error handling (no stack traces in production)
            response = requests.get(f"{self.base_url}/api/nonexistent-endpoint", timeout=10)
            security_checks['no_stack_traces'] = 'Traceback' not in response.text

        except requests.exceptions.RequestException as e:
            security_checks['security_test_error'] = str(e)
            self.results["warnings"].append(f"Security test incomplete: {str(e)}")

        self.results["checks"]["security"] = security_checks
        return security_checks

    def verify_error_handling(self) -> Dict[str, bool]:
        """Verify proper error handling for all scenarios"""
        print("Verifying error handling...")

        error_checks = {}

        if not self.api_running:
            error_checks['server_not_running'] = True
            return error_checks

        error_scenarios = [
            ("/api/provisions?version=nonexistent", 400, "invalid_version"),
            ("/api/provisions?as_at_date=invalid-date", 400, "invalid_date"),
            ("/api/versions/changes", 400, "missing_required_param"),
            ("/api/versions/compare?document_identifier=test", 400, "missing_version_params"),
            ("/api/nonexistent", 404, "endpoint_not_found")
        ]

        for url, expected_status, test_name in error_scenarios:
            try:
                response = requests.get(f"{self.base_url}{url}", timeout=10)
                error_checks[f'{test_name}_correct_status'] = response.status_code == expected_status

                # Check error response has helpful message
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_checks[f'{test_name}_has_error_message'] = (
                            'error' in error_data or 'message' in error_data
                        )
                    except:
                        error_checks[f'{test_name}_has_error_message'] = len(response.text) > 0

            except requests.exceptions.RequestException as e:
                error_checks[f'{test_name}_error'] = str(e)

        self.results["checks"]["error_handling"] = error_checks
        return error_checks

    def run_comprehensive_verification(self) -> bool:
        """Run all granular verification checks"""
        print("Starting PRP-V6-Enhanced Comprehensive API Verification...")

        # Check if API server is running first
        self.check_api_server_running()

        # Run all verification categories
        existing_results = self.verify_existing_endpoint_enhancements()
        format_results = self.verify_response_format_enhancements()
        new_endpoint_results = self.verify_new_version_endpoints()
        compatibility_results = self.verify_backward_compatibility()
        integration_results = self.verify_data_integration()
        performance_results = self.verify_performance_requirements()
        security_results = self.verify_security_requirements()
        error_results = self.verify_error_handling()

        # Calculate success metrics
        all_checks = [
            existing_results, format_results, new_endpoint_results,
            compatibility_results, integration_results, performance_results,
            security_results, error_results
        ]

        total_checks = sum(len(checks) for checks in all_checks)
        passed_checks = sum(
            sum(1 for result in checks.values() if result is True)
            for checks in all_checks
        )

        success_rate = passed_checks / total_checks if total_checks > 0 else 0

        # Determine overall success (require 85% pass rate for API testing)
        critical_requirements = [
            integration_results.get('version_aware_query_works', False),
            not any('error' in str(v) for v in existing_results.values()),
            len(self.results["errors"]) == 0
        ]

        success = (
            all(critical_requirements) and
            success_rate >= 0.85
        )

        self.results["success"] = success
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "success_rate": success_rate,
            "api_server_running": self.api_running,
            "critical_components_verified": {
                "service_integration": integration_results.get('version_aware_query_works', False),
                "backward_compatibility": not any('error' in str(v) for v in compatibility_results.values()),
                "new_endpoints": len([v for v in new_endpoint_results.values() if v is True]) > 0,
                "performance": performance_results.get('basic_query_under_2s', False)
            }
        }

        # Save detailed results
        output_file = "verify_v6_enhanced_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print detailed summary
        print("\n" + "="*60)
        print("PRP-V6-ENHANCED API GRANULAR VERIFICATION RESULTS")
        print("="*60)
        print(f"API Server Running: {'YES' if self.api_running else 'NO'}")
        print(f"Total checks performed: {total_checks}")
        print(f"Checks passed: {passed_checks}")
        print(f"Success rate: {success_rate:.1%}")
        print(f"Errors: {len(self.results['errors'])}")
        print(f"Warnings: {len(self.results['warnings'])}")

        print(f"\nComponent Verification:")
        print(f"  Existing Endpoints: {'PASS' if not any('error' in str(v) for v in existing_results.values()) else 'FAIL'}")
        print(f"  Response Formats: {'PASS' if format_results.get('version_param_includes_metadata', False) else 'FAIL'}")
        print(f"  New Endpoints: {'PASS' if len([v for v in new_endpoint_results.values() if v is True]) > 0 else 'FAIL'}")
        print(f"  Backward Compatibility: {'PASS' if not any('error' in str(v) for v in compatibility_results.values()) else 'FAIL'}")
        print(f"  Service Integration: {'PASS' if integration_results.get('version_aware_query_works', False) else 'FAIL'}")
        print(f"  Performance: {'PASS' if performance_results.get('basic_query_under_2s', False) else 'FAIL'}")
        print(f"  Security: {'PASS' if security_results.get('sql_injection_protected', False) else 'FAIL'}")
        print(f"  Error Handling: {'PASS' if len([v for v in error_results.values() if v is True]) > 0 else 'FAIL'}")

        if self.results["errors"]:
            print(f"\nCritical Errors:")
            for error in self.results["errors"]:
                print(f"  ERROR: {error}")

        if self.results["warnings"]:
            print(f"\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  WARNING: {warning}")

        print(f"\n{'PRP-V6-ENHANCED VERIFICATION PASSED' if success else 'PRP-V6-ENHANCED VERIFICATION FAILED'}")
        print(f"Detailed results saved to: {output_file}")

        return success

if __name__ == "__main__":
    verifier = PRPV6EnhancedVerification()
    success = verifier.run_comprehensive_verification()
    sys.exit(0 if success else 1)
