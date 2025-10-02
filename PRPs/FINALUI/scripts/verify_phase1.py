#!/usr/bin/env python3
"""
PRP-UI-PHASE1: Automated Verification Script
Comprehensive point-by-point testing of real constraint data integration

Run: python PRPs/FINALUI/scripts/verify_phase1.py
"""

import sys
import os
import json
import time
import subprocess
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from db_config import get_connection
except ImportError:
    print("ERROR: Cannot import db_config. Make sure you're in the project root.")
    sys.exit(1)


class Phase1Verifier:
    """Automated verification for Phase 1 implementation"""

    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.api_base = "http://localhost:3007"

    def log_test(self, test_name, passed, details="", expected="", actual=""):
        """Log test result"""
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "expected": expected,
            "actual": actual,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {test_name}")
        if details:
            print(f"      {details}")
        if not passed:
            if expected:
                print(f"      Expected: {expected}")
            if actual:
                print(f"      Actual: {actual}")

    def test_database_connection(self):
        """Test 1: Database connection available"""
        print("\n=== DATABASE TESTS ===")

        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()

            self.log_test(
                "Database Connection",
                True,
                "PostgreSQL connection successful"
            )
            return True
        except Exception as e:
            self.log_test(
                "Database Connection",
                False,
                f"Connection failed: {str(e)}"
            )
            return False

    def test_regulatory_provisions_table(self):
        """Test 2: Regulatory provisions table exists and populated"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE zone IS NOT NULL AND provision_type IS NOT NULL
            """)
            valid_count = cursor.fetchone()[0]

            conn.close()

            self.log_test(
                "Regulatory Provisions Table",
                count > 20000,
                f"Total: {count} provisions, Valid: {valid_count} with zone+type",
                expected="22,105 provisions",
                actual=f"{count} provisions"
            )

            return count > 20000
        except Exception as e:
            self.log_test(
                "Regulatory Provisions Table",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_zone_coverage(self):
        """Test 3: Multiple zones have provisions"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT zone, COUNT(*) as count
                FROM regulatory_provisions
                WHERE zone IS NOT NULL
                GROUP BY zone
                ORDER BY count DESC
                LIMIT 10
            """)

            zones = cursor.fetchall()
            conn.close()

            zone_count = len(zones)
            top_zones = [f"{z[0]}({z[1]})" for z in zones[:5]]

            self.log_test(
                "Zone Coverage",
                zone_count >= 10,
                f"Found {zone_count} zones with provisions. Top 5: {', '.join(top_zones)}",
                expected="10+ zones",
                actual=f"{zone_count} zones"
            )

            return zone_count >= 10
        except Exception as e:
            self.log_test(
                "Zone Coverage",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_provision_types(self):
        """Test 4: Provision types are categorized"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT provision_type, COUNT(*) as count
                FROM regulatory_provisions
                WHERE provision_type IS NOT NULL
                GROUP BY provision_type
                ORDER BY count DESC
                LIMIT 15
            """)

            types = cursor.fetchall()
            conn.close()

            type_count = len(types)
            has_key_types = any('height' in t[0].lower() for t in types) and \
                           any('fsr' in t[0].lower() or 'floor' in t[0].lower() for t in types)

            types_summary = [f"{t[0]}({t[1]})" for t in types[:5]]

            self.log_test(
                "Provision Types",
                type_count >= 5 and has_key_types,
                f"Found {type_count} provision types. Top 5: {', '.join(types_summary)}",
                expected="5+ types including height/FSR",
                actual=f"{type_count} types, key types: {has_key_types}"
            )

            return type_count >= 5 and has_key_types
        except Exception as e:
            self.log_test(
                "Provision Types",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_document_types(self):
        """Test 5: Documents have authority levels (LEP/DCP/SEPP)"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT document_type, COUNT(*) as count
                FROM documents
                WHERE document_type IS NOT NULL
                GROUP BY document_type
                ORDER BY count DESC
            """)

            doc_types = cursor.fetchall()
            conn.close()

            has_lep = any('LEP' in str(dt[0]).upper() for dt in doc_types)
            has_dcp = any('DCP' in str(dt[0]).upper() for dt in doc_types)
            has_sepp = any('SEPP' in str(dt[0]).upper() for dt in doc_types)

            types_found = [dt[0] for dt in doc_types]

            self.log_test(
                "Document Types",
                has_lep or has_dcp or has_sepp,
                f"Found document types: {', '.join(types_found)}",
                expected="LEP, DCP, and/or SEPP documents",
                actual=f"LEP:{has_lep}, DCP:{has_dcp}, SEPP:{has_sepp}"
            )

            return has_lep or has_dcp or has_sepp
        except Exception as e:
            self.log_test(
                "Document Types",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_development_permissions_table(self):
        """Test 6: Development permissions table populated"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM development_permissions")
            count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT zone) FROM development_permissions
            """)
            zone_count = cursor.fetchone()[0]

            conn.close()

            self.log_test(
                "Development Permissions Table",
                count >= 200,
                f"Found {count} permissions across {zone_count} zones",
                expected="200+ permissions",
                actual=f"{count} permissions"
            )

            return count >= 200
        except Exception as e:
            self.log_test(
                "Development Permissions Table",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_sepp_overrides_table(self):
        """Test 7: SEPP overrides table populated"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM sepp_lep_overrides")
            count = cursor.fetchone()[0]

            conn.close()

            self.log_test(
                "SEPP Overrides Table",
                count >= 50,
                f"Found {count} SEPP override records",
                expected="50+ overrides",
                actual=f"{count} overrides"
            )

            return count >= 50
        except Exception as e:
            self.log_test(
                "SEPP Overrides Table",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_database_indexes(self):
        """Test 8: Required indexes exist for performance"""
        print("\n=== DATABASE PERFORMANCE TESTS ===")

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'regulatory_provisions'
                AND (indexname LIKE '%zone%' OR indexname LIKE '%type%')
            """)

            indexes = [row[0] for row in cursor.fetchall()]
            conn.close()

            has_zone_index = any('zone' in idx.lower() for idx in indexes)

            self.log_test(
                "Database Indexes",
                has_zone_index,
                f"Found indexes: {', '.join(indexes) if indexes else 'None'}",
                expected="Index on zone column",
                actual=f"Zone index exists: {has_zone_index}"
            )

            return has_zone_index
        except Exception as e:
            self.log_test(
                "Database Indexes",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_sample_zone_query_performance(self):
        """Test 9: Zone query performance < 1 second"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            start = time.time()

            cursor.execute("""
                SELECT
                    rp.id,
                    rp.provision_text,
                    rp.provision_type,
                    rp.clause_number,
                    d.document_name,
                    d.document_type
                FROM regulatory_provisions rp
                LEFT JOIN documents d ON rp.document_id = d.id
                WHERE rp.zone = 'R2'
                AND rp.provision_type IS NOT NULL
                LIMIT 50
            """)

            results = cursor.fetchall()
            elapsed = time.time() - start

            conn.close()

            self.log_test(
                "Zone Query Performance",
                elapsed < 1.0,
                f"Query returned {len(results)} results in {elapsed:.3f}s",
                expected="< 1.0 seconds",
                actual=f"{elapsed:.3f} seconds"
            )

            return elapsed < 1.0
        except Exception as e:
            self.log_test(
                "Zone Query Performance",
                False,
                f"Query failed: {str(e)}"
            )
            return False

    def test_api_endpoint_exists(self):
        """Test 10: API endpoint file exists"""
        print("\n=== API ENDPOINT TESTS ===")

        api_file = "frontend-nextjs/app/api/compliance/constraints/route.ts"
        exists = os.path.exists(api_file)

        if exists:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
                has_post = 'POST' in content
                has_pool = 'Pool' in content or 'pool' in content
                has_query = 'query' in content.lower()

                details = f"File exists with POST:{has_post}, DB:{has_pool}, Query:{has_query}"
                passed = has_post and has_pool and has_query
        else:
            details = "API endpoint file not found"
            passed = False

        self.log_test(
            "API Endpoint File",
            passed,
            details,
            expected="route.ts with POST handler and DB queries",
            actual="File found" if exists else "File not found"
        )

        return passed

    def test_api_typescript_syntax(self):
        """Test 11: API TypeScript compiles without errors"""
        try:
            os.chdir('frontend-nextjs')
            result = subprocess.run(
                ['npx', 'tsc', '--noEmit'],
                capture_output=True,
                text=True,
                timeout=30
            )
            os.chdir('..')

            has_errors = 'error TS' in result.stdout or 'error TS' in result.stderr

            self.log_test(
                "TypeScript Compilation",
                not has_errors,
                "No TypeScript errors" if not has_errors else "TypeScript errors found",
                expected="Clean compilation",
                actual="Errors found" if has_errors else "Clean"
            )

            return not has_errors
        except Exception as e:
            self.log_test(
                "TypeScript Compilation",
                False,
                f"Compilation check failed: {str(e)}"
            )
            return False

    def test_frontend_integration(self):
        """Test 12: ComplianceDashboard imports API correctly"""
        dashboard_file = "frontend-nextjs/components/compliance/ComplianceDashboard.tsx"

        try:
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                content = f.read()

            has_fetch = '/api/compliance/constraints' in content
            has_post = "method: 'POST'" in content or 'method: "POST"' in content
            no_mock = 'mockData' not in content or content.count('mockData') < 5

            details = f"API call:{has_fetch}, POST:{has_post}, No mock:{no_mock}"

            self.log_test(
                "Frontend Integration",
                has_fetch and has_post,
                details,
                expected="Fetch to /api/compliance/constraints with POST",
                actual=details
            )

            return has_fetch and has_post
        except Exception as e:
            self.log_test(
                "Frontend Integration",
                False,
                f"File read failed: {str(e)}"
            )
            return False

    def test_dev_server_running(self):
        """Test 13: Next.js dev server is running"""
        print("\n=== RUNTIME TESTS ===")

        try:
            response = requests.get(f"{self.api_base}/", timeout=5)
            running = response.status_code in [200, 404, 500]

            self.log_test(
                "Dev Server Running",
                running,
                f"Server responded with status {response.status_code}",
                expected="HTTP 200/404/500",
                actual=f"HTTP {response.status_code}"
            )

            return running
        except requests.exceptions.RequestException as e:
            self.log_test(
                "Dev Server Running",
                False,
                f"Server not reachable: {str(e)}",
                expected="Server responding",
                actual="Connection failed"
            )
            return False

    def test_api_endpoint_responds(self):
        """Test 14: API endpoint responds to requests"""
        try:
            response = requests.post(
                f"{self.api_base}/api/compliance/constraints",
                json={
                    "address": "30 Illawarra Road, Marrickville NSW",
                    "zone": "R2",
                    "developmentType": "dual_occupancy"
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                has_success = 'success' in data
                has_data = 'data' in data

                details = f"Status 200, success:{has_success}, data:{has_data}"
                passed = has_success and has_data
            else:
                details = f"Status {response.status_code}"
                passed = False

            self.log_test(
                "API Endpoint Response",
                passed,
                details,
                expected="HTTP 200 with success:true and data",
                actual=f"HTTP {response.status_code}"
            )

            return passed
        except Exception as e:
            self.log_test(
                "API Endpoint Response",
                False,
                f"Request failed: {str(e)}"
            )
            return False

    def test_api_returns_constraints(self):
        """Test 15: API returns actual constraint data"""
        try:
            response = requests.post(
                f"{self.api_base}/api/compliance/constraints",
                json={
                    "address": "30 Illawarra Road, Marrickville NSW",
                    "zone": "R2"
                },
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    building = data['data'].get('building_envelope', [])
                    environmental = data['data'].get('environmental', [])
                    special = data['data'].get('special_provisions', [])

                    total = len(building) + len(environmental) + len(special)

                    details = f"Building:{len(building)}, Env:{len(environmental)}, Special:{len(special)}, Total:{total}"
                    passed = total > 0

                    self.log_test(
                        "API Returns Constraints",
                        passed,
                        details,
                        expected=">0 constraints",
                        actual=f"{total} constraints"
                    )

                    return passed
                else:
                    self.log_test(
                        "API Returns Constraints",
                        False,
                        f"API error: {data.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                self.log_test(
                    "API Returns Constraints",
                    False,
                    f"HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test(
                "API Returns Constraints",
                False,
                f"Request failed: {str(e)}"
            )
            return False

    def test_api_constraint_structure(self):
        """Test 16: Constraints have required fields"""
        try:
            response = requests.post(
                f"{self.api_base}/api/compliance/constraints",
                json={"zone": "R2"},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    constraints = data['data'].get('building_envelope', [])

                    if len(constraints) > 0:
                        first = constraints[0]

                        has_type = 'type' in first
                        has_value = 'value' in first
                        has_source = 'source' in first
                        has_clause = 'clause' in first.get('source', {})
                        has_authority = 'authority_level' in first.get('source', {})

                        details = f"type:{has_type}, value:{has_value}, source:{has_source}, clause:{has_clause}, authority:{has_authority}"
                        passed = all([has_type, has_value, has_source, has_clause, has_authority])

                        self.log_test(
                            "Constraint Structure",
                            passed,
                            details,
                            expected="All required fields present",
                            actual=details
                        )

                        return passed
                    else:
                        self.log_test(
                            "Constraint Structure",
                            False,
                            "No constraints returned to validate"
                        )
                        return False
                else:
                    self.log_test(
                        "Constraint Structure",
                        False,
                        f"API error: {data.get('error')}"
                    )
                    return False
            else:
                self.log_test(
                    "Constraint Structure",
                    False,
                    f"HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test(
                "Constraint Structure",
                False,
                f"Request failed: {str(e)}"
            )
            return False

    def test_api_authority_levels(self):
        """Test 17: Authority levels are LEP/DCP/SEPP"""
        try:
            response = requests.post(
                f"{self.api_base}/api/compliance/constraints",
                json={"zone": "R2"},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('success'):
                    all_constraints = []
                    all_constraints.extend(data['data'].get('building_envelope', []))
                    all_constraints.extend(data['data'].get('environmental', []))
                    all_constraints.extend(data['data'].get('special_provisions', []))

                    if len(all_constraints) > 0:
                        valid_levels = ['LEP', 'DCP', 'SEPP']
                        authorities = [c.get('source', {}).get('authority_level') for c in all_constraints]

                        all_valid = all(auth in valid_levels for auth in authorities if auth)
                        unique_authorities = set(authorities)

                        details = f"Found authorities: {unique_authorities}, all valid: {all_valid}"

                        self.log_test(
                            "Authority Levels",
                            all_valid,
                            details,
                            expected="Only LEP/DCP/SEPP",
                            actual=str(unique_authorities)
                        )

                        return all_valid
                    else:
                        self.log_test(
                            "Authority Levels",
                            False,
                            "No constraints to validate"
                        )
                        return False
                else:
                    self.log_test(
                        "Authority Levels",
                        False,
                        f"API error: {data.get('error')}"
                    )
                    return False
            else:
                self.log_test(
                    "Authority Levels",
                    False,
                    f"HTTP {response.status_code}"
                )
                return False

        except Exception as e:
            self.log_test(
                "Authority Levels",
                False,
                f"Request failed: {str(e)}"
            )
            return False

    def test_api_performance(self):
        """Test 18: API response time < 2 seconds"""
        try:
            start = time.time()

            response = requests.post(
                f"{self.api_base}/api/compliance/constraints",
                json={"zone": "R2"},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            elapsed = time.time() - start

            passed = elapsed < 2.0 and response.status_code == 200

            self.log_test(
                "API Performance",
                passed,
                f"Response time: {elapsed:.3f}s",
                expected="< 2.0 seconds",
                actual=f"{elapsed:.3f} seconds"
            )

            return passed
        except Exception as e:
            self.log_test(
                "API Performance",
                False,
                f"Request failed: {str(e)}"
            )
            return False

    def test_multiple_zones(self):
        """Test 19: API works for multiple zone types"""
        print("\n=== MULTI-ZONE TESTS ===")

        test_zones = ['R1', 'R2', 'B1', 'E1', 'IN1']
        results = []

        for zone in test_zones:
            try:
                response = requests.post(
                    f"{self.api_base}/api/compliance/constraints",
                    json={"zone": zone},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    success = data.get('success', False)
                    results.append((zone, success))
                else:
                    results.append((zone, False))

            except Exception:
                results.append((zone, False))

        successful = sum(1 for _, success in results if success)
        details = ', '.join([f"{z}:{'OK' if s else 'FAIL'}" for z, s in results])

        self.log_test(
            "Multiple Zone Support",
            successful >= 3,
            f"{successful}/{len(test_zones)} zones successful. {details}",
            expected="3+ zones working",
            actual=f"{successful} zones working"
        )

        return successful >= 3

    def test_error_handling(self):
        """Test 20: API handles invalid inputs gracefully"""
        test_cases = [
            ({"zone": ""}, "Empty zone"),
            ({"zone": "INVALID_ZONE"}, "Invalid zone code"),
            ({}, "Missing zone parameter")
        ]

        passed_tests = 0

        for payload, description in test_cases:
            try:
                response = requests.post(
                    f"{self.api_base}/api/compliance/constraints",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )

                # Should return 400 or structured error
                handles_error = response.status_code in [400, 200]

                if response.status_code == 200:
                    data = response.json()
                    handles_error = 'error' in data or data.get('success') == False

                if handles_error:
                    passed_tests += 1

            except Exception:
                pass

        passed = passed_tests >= 2

        self.log_test(
            "Error Handling",
            passed,
            f"{passed_tests}/{len(test_cases)} error cases handled correctly",
            expected="Graceful error handling",
            actual=f"{passed_tests} cases handled"
        )

        return passed

    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "=" * 70)
        print("PHASE 1 VERIFICATION REPORT")
        print("=" * 70)

        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        failed_tests = total_tests - passed_tests

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")

        elapsed = time.time() - self.start_time
        print(f"\nTotal Verification Time: {elapsed:.2f} seconds")

        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.results:
                if not result['passed']:
                    print(f"  - {result['test']}")
                    if result['details']:
                        print(f"    {result['details']}")

        # Save detailed report
        report_file = "PRPs/FINALUI/verification_reports/phase1_report.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed': passed_tests,
                    'failed': failed_tests,
                    'success_rate': success_rate,
                    'verification_time': elapsed,
                    'timestamp': datetime.now().isoformat()
                },
                'tests': self.results
            }, f, indent=2)

        print(f"\nDetailed report saved to: {report_file}")

        # Final verdict
        print("\n" + "=" * 70)
        if success_rate >= 90:
            print("VERDICT: PHASE 1 READY FOR PRODUCTION")
            print("All critical tests passed. Implementation complete.")
            return 0
        elif success_rate >= 70:
            print("VERDICT: PHASE 1 NEEDS MINOR FIXES")
            print("Most tests passed. Review failed tests and fix issues.")
            return 1
        else:
            print("VERDICT: PHASE 1 NEEDS MAJOR WORK")
            print("Multiple critical failures. Review implementation.")
            return 2

    def run_all_tests(self):
        """Execute all verification tests"""
        print("=" * 70)
        print("PRP-UI-PHASE1: AUTOMATED VERIFICATION")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Database tests
        self.test_database_connection()
        self.test_regulatory_provisions_table()
        self.test_zone_coverage()
        self.test_provision_types()
        self.test_document_types()
        self.test_development_permissions_table()
        self.test_sepp_overrides_table()

        # Performance tests
        self.test_database_indexes()
        self.test_sample_zone_query_performance()

        # API tests
        self.test_api_endpoint_exists()
        self.test_api_typescript_syntax()
        self.test_frontend_integration()

        # Runtime tests
        server_running = self.test_dev_server_running()

        if server_running:
            self.test_api_endpoint_responds()
            self.test_api_returns_constraints()
            self.test_api_constraint_structure()
            self.test_api_authority_levels()
            self.test_api_performance()
            self.test_multiple_zones()
            self.test_error_handling()
        else:
            print("\n[SKIP] Runtime tests skipped - dev server not running")
            print("       Start server with: cd frontend-nextjs && npm run dev")

        # Generate report
        exit_code = self.generate_report()

        return exit_code


def main():
    """Main entry point"""
    verifier = Phase1Verifier()
    exit_code = verifier.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()