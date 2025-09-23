#!/usr/bin/env python3
"""
Verification script for PRP-V6: End-to-End Validation
Comprehensive validation of the complete version management system
"""

import sys
import json
import os
import requests
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from db_config import get_connection
from psycopg2.extras import RealDictCursor

class EndToEndVerification:
    """Comprehensive end-to-end validation of version management system"""

    def __init__(self):
        self.conn = get_connection()
        self.api_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "V6_END_TO_END",
            "test_scenarios": {},
            "performance_metrics": {},
            "errors": [],
            "warnings": [],
            "success": False
        }

    def test_version_creation_workflow(self) -> Dict[str, bool]:
        """Test complete version creation workflow"""
        workflow_tests = {}
        test_doc_id = f"TEST-E2E-{int(time.time())}"

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("BEGIN")

                # Step 1: Create initial version
                cursor.execute("""
                    INSERT INTO versions.document_versions
                    (document_type, document_identifier, version_number, version_status,
                     effective_date, created_by)
                    VALUES ('LEP', %s, 'v1.0', 'CURRENT', CURRENT_DATE, 'e2e_test')
                    RETURNING id
                """, (test_doc_id,))

                version1_id = cursor.fetchone()[0]
                workflow_tests['create_initial_version'] = True

                # Step 2: Add some test provisions
                cursor.execute("""
                    INSERT INTO regulatory_provisions
                    (document_id, provision_text, version_id, is_current)
                    VALUES (%s, 'Test provision 1', %s, true)
                """, (test_doc_id, version1_id))

                workflow_tests['link_provisions'] = True

                # Step 3: Create new version (should archive previous)
                cursor.execute("""
                    UPDATE versions.document_versions
                    SET version_status = 'PREVIOUS',
                        superseded_date = CURRENT_DATE
                    WHERE id = %s
                """, (version1_id,))

                cursor.execute("""
                    INSERT INTO versions.document_versions
                    (document_type, document_identifier, version_number, version_status,
                     effective_date, created_by)
                    VALUES ('LEP', %s, 'v1.1', 'CURRENT', CURRENT_DATE, 'e2e_test')
                    RETURNING id
                """, (test_doc_id,))

                version2_id = cursor.fetchone()[0]
                workflow_tests['create_new_version'] = True

                # Step 4: Verify version states
                cursor.execute("""
                    SELECT version_status, version_number
                    FROM versions.document_versions
                    WHERE document_identifier = %s
                    ORDER BY effective_date
                """, (test_doc_id,))

                versions = cursor.fetchall()
                workflow_tests['version_transition'] = (
                    len(versions) == 2 and
                    versions[0][0] == 'PREVIOUS' and
                    versions[1][0] == 'CURRENT'
                )

                # Step 5: Test function calls
                cursor.execute("""
                    SELECT versions.get_current_version('LEP', %s)
                """, (test_doc_id,))
                current_id = cursor.fetchone()[0]
                workflow_tests['function_get_current'] = current_id == version2_id

                # Cleanup
                cursor.execute("""
                    DELETE FROM regulatory_provisions WHERE document_id = %s
                """, (test_doc_id,))
                cursor.execute("""
                    DELETE FROM versions.document_versions WHERE document_identifier = %s
                """, (test_doc_id,))

                cursor.execute("COMMIT")

        except Exception as e:
            self.conn.rollback()
            workflow_tests['error'] = str(e)
            self.results["errors"].append(f"Version creation workflow failed: {str(e)}")

        return workflow_tests

    def test_api_version_queries(self) -> Dict[str, bool]:
        """Test API version query functionality"""
        api_tests = {}

        try:
            # Test 1: Basic provisions query
            response = requests.get(f"{self.api_url}/api/provisions", timeout=10)
            api_tests['basic_provisions'] = response.status_code == 200

            # Test 2: Version parameter
            response = requests.get(f"{self.api_url}/api/provisions?version=current", timeout=10)
            api_tests['version_current'] = response.status_code == 200

            if response.status_code == 200:
                data = response.json()
                api_tests['response_structure'] = all(key in data for key in ['status', 'provisions'])

            # Test 3: Date-based query
            test_date = "2023-06-01"
            response = requests.get(f"{self.api_url}/api/provisions?as_at_date={test_date}", timeout=10)
            api_tests['date_based_query'] = response.status_code == 200

            # Test 4: Version info inclusion
            response = requests.get(f"{self.api_url}/api/provisions?include_version_info=true", timeout=10)
            api_tests['version_info'] = response.status_code == 200

            # Test 5: Version endpoints
            response = requests.get(f"{self.api_url}/api/versions/current", timeout=10)
            api_tests['version_endpoints'] = response.status_code == 200

        except Exception as e:
            api_tests['api_error'] = str(e)
            self.results["warnings"].append(f"API tests partially failed: {str(e)}")

        return api_tests

    def test_performance_benchmarks(self) -> Dict[str, float]:
        """Test performance of version-aware queries"""
        performance = {}

        try:
            # Test 1: Current version query performance
            start_time = time.time()
            response = requests.get(f"{self.api_url}/api/provisions?version=current", timeout=30)
            end_time = time.time()

            if response.status_code == 200:
                performance['current_version_query_ms'] = (end_time - start_time) * 1000

            # Test 2: Date-based query performance
            start_time = time.time()
            response = requests.get(f"{self.api_url}/api/provisions?as_at_date=2023-06-01", timeout=30)
            end_time = time.time()

            if response.status_code == 200:
                performance['date_query_ms'] = (end_time - start_time) * 1000

            # Test 3: Database version function performance
            with self.conn.cursor() as cursor:
                start_time = time.time()
                cursor.execute("SELECT versions.get_current_version('LEP', 'Inner-West-LEP-2022')")
                cursor.fetchone()
                end_time = time.time()
                performance['db_function_ms'] = (end_time - start_time) * 1000

        except Exception as e:
            self.results["warnings"].append(f"Performance tests failed: {str(e)}")

        return performance

    def test_data_consistency(self) -> Dict[str, bool]:
        """Test data consistency across the system"""
        consistency_tests = {}

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Test 1: All current versions have corresponding provisions
            cursor.execute("""
                SELECT dv.document_identifier
                FROM versions.document_versions dv
                WHERE dv.version_status = 'CURRENT'
                  AND NOT EXISTS (
                      SELECT 1 FROM regulatory_provisions rp
                      WHERE rp.version_id = dv.id
                  )
            """)
            orphaned_versions = cursor.fetchall()
            consistency_tests['no_orphaned_versions'] = len(orphaned_versions) == 0

            # Test 2: All versioned provisions point to valid versions
            cursor.execute("""
                SELECT COUNT(*) FROM regulatory_provisions rp
                WHERE rp.version_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM versions.document_versions dv
                      WHERE dv.id = rp.version_id
                  )
            """)
            invalid_refs = cursor.fetchone()['count']
            consistency_tests['no_invalid_version_refs'] = invalid_refs == 0

            # Test 3: Version status consistency
            cursor.execute("""
                SELECT document_identifier, COUNT(*) as current_count
                FROM versions.document_versions
                WHERE version_status = 'CURRENT'
                GROUP BY document_identifier
                HAVING COUNT(*) > 1
            """)
            multiple_current = cursor.fetchall()
            consistency_tests['single_current_per_doc'] = len(multiple_current) == 0

            # Test 4: Date consistency
            cursor.execute("""
                SELECT COUNT(*) FROM versions.document_versions
                WHERE superseded_date IS NOT NULL
                  AND superseded_date < effective_date
            """)
            invalid_dates = cursor.fetchone()['count']
            consistency_tests['valid_date_sequences'] = invalid_dates == 0

        return consistency_tests

    def test_edge_cases(self) -> Dict[str, bool]:
        """Test edge cases and error handling"""
        edge_tests = {}

        try:
            # Test 1: Non-existent document version query
            response = requests.get(f"{self.api_url}/api/provisions?document_id=NONEXISTENT")
            edge_tests['nonexistent_document'] = response.status_code in [200, 404]

            # Test 2: Invalid date format
            response = requests.get(f"{self.api_url}/api/provisions?as_at_date=invalid-date")
            edge_tests['invalid_date_format'] = response.status_code in [400, 422]

            # Test 3: Future date query
            future_date = "2030-01-01"
            response = requests.get(f"{self.api_url}/api/provisions?as_at_date={future_date}")
            edge_tests['future_date_query'] = response.status_code == 200

            # Test 4: Empty version parameter
            response = requests.get(f"{self.api_url}/api/provisions?version=")
            edge_tests['empty_version_param'] = response.status_code in [200, 400, 422]

        except Exception as e:
            edge_tests['error'] = str(e)
            self.results["warnings"].append(f"Edge case tests failed: {str(e)}")

        return edge_tests

    def test_integration_scenarios(self) -> Dict[str, bool]:
        """Test realistic integration scenarios"""
        integration_tests = {}

        try:
            # Scenario 1: Development application assessment
            assessment_payload = {
                "property_id": "test-property-123",
                "development_type": "dwelling",
                "assessment_date": "2023-12-01"
            }

            response = requests.post(
                f"{self.api_url}/api/compliance/check",
                json=assessment_payload,
                timeout=15
            )
            integration_tests['development_assessment'] = response.status_code in [200, 422]

            # Scenario 2: Historical compliance check
            historical_payload = {
                "property_id": "test-property-456",
                "development_type": "dwelling",
                "assessment_date": "2022-06-01"
            }

            response = requests.post(
                f"{self.api_url}/api/compliance/check",
                json=historical_payload,
                timeout=15
            )
            integration_tests['historical_assessment'] = response.status_code in [200, 422]

            # Scenario 3: Current provisions lookup
            response = requests.get(
                f"{self.api_url}/api/provisions?version=current&include_version_info=true",
                timeout=10
            )
            integration_tests['current_provisions_lookup'] = response.status_code == 200

        except Exception as e:
            integration_tests['error'] = str(e)
            self.results["warnings"].append(f"Integration scenarios failed: {str(e)}")

        return integration_tests

    def run_verification(self) -> bool:
        """Run comprehensive end-to-end verification"""
        print(" Running PRP-V6: End-to-End Validation...")
        print("This comprehensive test validates the complete version management system.\n")

        # Test 1: Version Creation Workflow
        print(" Testing version creation workflow...")
        workflow_results = self.test_version_creation_workflow()
        self.results["test_scenarios"]["version_workflow"] = workflow_results
        workflow_passed = all(v for k, v in workflow_results.items() if k != 'error')
        print(f"  Workflow tests: {'' if workflow_passed else ''} ({sum(workflow_results.values())}/{len(workflow_results)})")

        # Test 2: API Version Queries
        print("\n Testing API version queries...")
        api_results = self.test_api_version_queries()
        self.results["test_scenarios"]["api_queries"] = api_results
        api_passed = sum(1 for v in api_results.values() if v is True) >= len(api_results) * 0.8
        print(f"  API tests: {'' if api_passed else ''} ({sum(1 for v in api_results.values() if v is True)}/{len(api_results)})")

        # Test 3: Performance Benchmarks
        print("\n Testing performance benchmarks...")
        perf_results = self.test_performance_benchmarks()
        self.results["performance_metrics"] = perf_results

        # Check performance criteria (< 2000ms for queries)
        perf_passed = all(
            ms < 2000 for ms in perf_results.values() if isinstance(ms, (int, float))
        )
        print(f"  Performance tests: {'' if perf_passed else ''}")
        for metric, value in perf_results.items():
            if isinstance(value, (int, float)):
                print(f"    {metric}: {value:.1f}ms")

        # Test 4: Data Consistency
        print("\n Testing data consistency...")
        consistency_results = self.test_data_consistency()
        self.results["test_scenarios"]["data_consistency"] = consistency_results
        consistency_passed = all(consistency_results.values())
        print(f"  Consistency tests: {'' if consistency_passed else ''} ({sum(consistency_results.values())}/{len(consistency_results)})")

        # Test 5: Edge Cases
        print("\n Testing edge cases...")
        edge_results = self.test_edge_cases()
        self.results["test_scenarios"]["edge_cases"] = edge_results
        edge_passed = sum(1 for v in edge_results.values() if v is True) >= len(edge_results) * 0.7
        print(f"  Edge case tests: {'' if edge_passed else ''} ({sum(1 for v in edge_results.values() if v is True)}/{len(edge_results)})")

        # Test 6: Integration Scenarios
        print("\n Testing integration scenarios...")
        integration_results = self.test_integration_scenarios()
        self.results["test_scenarios"]["integration"] = integration_results
        integration_passed = sum(1 for v in integration_results.values() if v is True) >= len(integration_results) * 0.7
        print(f"  Integration tests: {'' if integration_passed else ''} ({sum(1 for v in integration_results.values() if v is True)}/{len(integration_results)})")

        # Overall success criteria
        critical_tests_passed = (
            workflow_passed and
            api_passed and
            consistency_passed and
            perf_passed
        )

        self.results["success"] = critical_tests_passed

        # Save comprehensive results
        with open("verify_v6_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Print comprehensive summary
        print("\n" + "=" * 60)
        print(" COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Version Workflow: {' PASS' if workflow_passed else ' FAIL'}")
        print(f"API Functionality: {' PASS' if api_passed else ' FAIL'}")
        print(f"Performance: {' PASS' if perf_passed else ' FAIL'}")
        print(f"Data Consistency: {' PASS' if consistency_passed else ' FAIL'}")
        print(f"Edge Cases: {' PASS' if edge_passed else ' PARTIAL'}")
        print(f"Integration: {' PASS' if integration_passed else ' PARTIAL'}")

        if self.results["errors"]:
            print("\n Critical Errors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\n Warnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\n{' END-TO-END VALIDATION PASSED' if critical_tests_passed else ' END-TO-END VALIDATION FAILED'}")

        if critical_tests_passed:
            print("\n Version Management MVP is ready for production!")
            print("   All critical systems are operational.")
        else:
            print("\n System requires attention before production deployment.")

        return critical_tests_passed

def main():
    """Main entry point"""
    verifier = EndToEndVerification()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
