#!/usr/bin/env python3
"""
PRP-Q1 Verification Script
=========================
Verifies that BASIX and Special Provisions Integration is properly implemented
"""

from db_config import get_connection
import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any

class PRPQ1Verifier:
    """Automated verification for PRP-Q1 implementation"""

    def __init__(self):
        self.results = {
            'verification_id': 'PRP-Q1-VERIFICATION',
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {}
        }

    def verify_basix_schema(self) -> Dict:
        """Verify BASIX provisions table and data"""
        print("🔍 Verifying BASIX Schema and Data...")

        test_result = {
            'test': 'basix_schema',
            'passed': False,
            'details': {}
        }

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'basix_provisions'
                )
            """)
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                test_result['error'] = 'BASIX provisions table does not exist'
                return test_result

            # Check table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'basix_provisions'
                ORDER BY column_name
            """)
            columns = cursor.fetchall()

            expected_columns = {
                'climate_zone', 'development_type', 'energy_reduction_target',
                'water_reduction_target', 'thermal_comfort_rating', 'tier_level'
            }
            actual_columns = {col[0] for col in columns}

            missing_columns = expected_columns - actual_columns
            if missing_columns:
                test_result['error'] = f'Missing columns: {missing_columns}'
                return test_result

            test_result['details']['table_structure'] = 'VALID'

            # Check data completeness
            cursor.execute("SELECT COUNT(*) FROM basix_provisions")
            total_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT climate_zone) as zones,
                       COUNT(DISTINCT development_type) as dev_types
                FROM basix_provisions
            """)
            distinct_counts = cursor.fetchone()

            test_result['details']['total_provisions'] = total_count
            test_result['details']['climate_zones'] = distinct_counts[0]
            test_result['details']['development_types'] = distinct_counts[1]

            # Verify specific test cases
            test_cases = [
                ('Zone 17', 'dwelling_house'),
                ('Zone 18', 'residential_flat_building'),
                ('Zone 19', 'dwelling_house')
            ]

            verified_cases = 0
            for climate_zone, dev_type in test_cases:
                cursor.execute("""
                    SELECT energy_reduction_target, water_reduction_target
                    FROM basix_provisions
                    WHERE climate_zone = %s AND development_type = %s
                """, (climate_zone, dev_type))

                result = cursor.fetchone()
                if result and result[0] is not None and result[1] is not None:
                    verified_cases += 1

            test_result['details']['verified_test_cases'] = f'{verified_cases}/{len(test_cases)}'

            # Pass if we have data and key test cases work
            test_result['passed'] = (
                total_count >= 5 and
                distinct_counts[0] >= 2 and  # At least 2 climate zones
                distinct_counts[1] >= 3 and  # At least 3 development types
                verified_cases >= 2          # At least 2 test cases work
            )

            conn.close()

            if test_result['passed']:
                print(f"✅ BASIX Schema: {total_count} provisions across {distinct_counts[0]} zones")
            else:
                print(f"❌ BASIX Schema: Insufficient data coverage")

        except Exception as e:
            test_result['error'] = str(e)
            print(f"❌ BASIX Schema verification failed: {e}")

        return test_result

    def verify_special_provisions_schema(self) -> Dict:
        """Verify special provisions registry and related tables"""
        print("🔍 Verifying Special Provisions Schema...")

        test_result = {
            'test': 'special_provisions_schema',
            'passed': False,
            'details': {}
        }

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Check all required tables exist
            required_tables = [
                'special_provisions_registry',
                'provision_thresholds',
                'provision_implications'
            ]

            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    )
                """, (table,))
                exists = cursor.fetchone()[0]

                if not exists:
                    test_result['error'] = f'Table {table} does not exist'
                    return test_result

            test_result['details']['tables_created'] = 'ALL_EXIST'

            # Check registry data
            cursor.execute("SELECT COUNT(*) FROM special_provisions_registry")
            registry_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT provision_type, COUNT(*) as count
                FROM special_provisions_registry
                WHERE active = TRUE
                GROUP BY provision_type
                ORDER BY count DESC
                LIMIT 5
            """)
            provision_types = cursor.fetchall()

            test_result['details']['registry_provisions'] = registry_count
            test_result['details']['provision_types'] = [
                {'type': ptype, 'count': count} for ptype, count in provision_types
            ]

            # Check critical provision types exist
            critical_types = [
                'Climate Zones',
                'Flood Planning',
                'Bushfire Prone Land',
                'State Environmental Planning Policy'
            ]

            existing_types = {ptype for ptype, _ in provision_types}
            missing_critical = set(critical_types) - existing_types

            if missing_critical:
                test_result['details']['missing_critical_types'] = list(missing_critical)
            else:
                test_result['details']['critical_types'] = 'ALL_PRESENT'

            test_result['passed'] = (
                registry_count >= 5 and
                len(missing_critical) == 0
            )

            conn.close()

            if test_result['passed']:
                print(f"✅ Special Provisions Schema: {registry_count} provision types registered")
            else:
                print(f"❌ Special Provisions Schema: Missing critical types or insufficient data")

        except Exception as e:
            test_result['error'] = str(e)
            print(f"❌ Special Provisions Schema verification failed: {e}")

        return test_result

    def verify_basix_service(self) -> Dict:
        """Verify BASIX compliance checker service"""
        print("🔍 Verifying BASIX Compliance Service...")

        test_result = {
            'test': 'basix_service',
            'passed': False,
            'details': {}
        }

        try:
            # Check service file exists
            service_file = 'services/basix_compliance_checker.py'
            if not os.path.exists(service_file):
                test_result['error'] = f'Service file {service_file} does not exist'
                return test_result

            test_result['details']['service_file'] = 'EXISTS'

            # Try to import and test the service
            import sys
            sys.path.append('services')

            try:
                from basix_compliance_checker import BASIXComplianceChecker

                checker = BASIXComplianceChecker()
                test_result['details']['service_import'] = 'SUCCESS'

                # Test service functionality
                test_case = checker.process_basix_for_compliance('Zone 17', 'dwelling_house')

                if test_case and test_case.get('basix_applicable'):
                    provisions = test_case.get('tier_1_provisions', [])
                    test_result['details']['test_provisions_count'] = len(provisions)

                    # Check for key provision types
                    provision_types = {prov.get('provision_type') for prov in provisions}
                    expected_types = {'energy_efficiency', 'water_efficiency'}

                    if expected_types.issubset(provision_types):
                        test_result['details']['provision_types'] = 'COMPLETE'
                        test_result['passed'] = True
                    else:
                        test_result['details']['missing_provision_types'] = list(expected_types - provision_types)
                else:
                    test_result['error'] = 'Service test returned no applicable BASIX requirements'

            except ImportError as e:
                test_result['error'] = f'Failed to import service: {e}'
            except Exception as e:
                test_result['error'] = f'Service test failed: {e}'

            if test_result['passed']:
                print(f"✅ BASIX Service: Working with {test_result['details']['test_provisions_count']} provisions")
            else:
                print(f"❌ BASIX Service: {test_result.get('error', 'Test failed')}")

        except Exception as e:
            test_result['error'] = str(e)
            print(f"❌ BASIX Service verification failed: {e}")

        return test_result

    def verify_api_integration(self) -> Dict:
        """Verify enhanced compliance API integration"""
        print("🔍 Verifying API Integration...")

        test_result = {
            'test': 'api_integration',
            'passed': False,
            'details': {}
        }

        try:
            # Check enhanced API file exists
            api_file = 'services/enhanced_compliance_api.py'
            if os.path.exists(api_file):
                with open(api_file, 'r') as f:
                    api_content = f.read()

                # Check for BASIX integration indicators
                integration_indicators = [
                    'BASIXComplianceChecker',
                    'check_compliance_with_basix',
                    'climate_zone',
                    'basix_requirements'
                ]

                found_indicators = [
                    indicator for indicator in integration_indicators
                    if indicator in api_content
                ]

                test_result['details']['integration_indicators'] = {
                    'found': found_indicators,
                    'missing': [ind for ind in integration_indicators if ind not in found_indicators]
                }

                # Try to test the API
                try:
                    import sys
                    sys.path.append('services')
                    from enhanced_compliance_api import EnhancedComplianceAPI

                    api = EnhancedComplianceAPI()
                    test_result['details']['api_import'] = 'SUCCESS'

                    # Test API functionality
                    test_property_data = {
                        'constraints': [
                            {'Type': 'Climate Zones', 'Class': 'Zone 17'}
                        ]
                    }

                    api_result = api.check_compliance_with_basix(
                        'R2', 'dwelling_house', test_property_data
                    )

                    if api_result and 'basix_requirements' in api_result:
                        test_result['details']['api_test'] = 'SUCCESS'
                        test_result['details']['basix_climate_zone'] = api_result.get('climate_zone')
                        test_result['passed'] = True
                    else:
                        test_result['error'] = 'API test did not return BASIX requirements'

                except ImportError as e:
                    test_result['error'] = f'Failed to import enhanced API: {e}'
                except Exception as e:
                    test_result['error'] = f'API test failed: {e}'

                if len(found_indicators) >= 3:
                    test_result['details']['code_integration'] = 'GOOD'
                else:
                    test_result['details']['code_integration'] = 'INCOMPLETE'

            else:
                test_result['error'] = f'Enhanced API file {api_file} does not exist'

            if test_result['passed']:
                print(f"✅ API Integration: BASIX functionality integrated and working")
            else:
                print(f"❌ API Integration: {test_result.get('error', 'Integration incomplete')}")

        except Exception as e:
            test_result['error'] = str(e)
            print(f"❌ API Integration verification failed: {e}")

        return test_result

    def verify_data_completeness(self) -> Dict:
        """Verify data completeness and coverage"""
        print("🔍 Verifying Data Completeness...")

        test_result = {
            'test': 'data_completeness',
            'passed': False,
            'details': {}
        }

        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Check BASIX data coverage
            cursor.execute("""
                SELECT
                    climate_zone,
                    COUNT(DISTINCT development_type) as dev_types,
                    COUNT(*) as total_provisions,
                    AVG(energy_reduction_target) as avg_energy_target,
                    AVG(water_reduction_target) as avg_water_target
                FROM basix_provisions
                GROUP BY climate_zone
                ORDER BY climate_zone
            """)

            basix_coverage = cursor.fetchall()
            test_result['details']['basix_coverage'] = [
                {
                    'climate_zone': row[0],
                    'development_types': row[1],
                    'provisions': row[2],
                    'avg_energy_target': float(row[3]) if row[3] else 0,
                    'avg_water_target': float(row[4]) if row[4] else 0
                }
                for row in basix_coverage
            ]

            # Check provision registry coverage
            cursor.execute("""
                SELECT
                    default_tier_level,
                    COUNT(*) as provision_count,
                    COUNT(CASE WHEN requires_specialist THEN 1 END) as specialist_count
                FROM special_provisions_registry
                WHERE active = TRUE
                GROUP BY default_tier_level
                ORDER BY default_tier_level
            """)

            tier_coverage = cursor.fetchall()
            test_result['details']['tier_coverage'] = [
                {
                    'tier': row[0],
                    'provision_count': row[1],
                    'specialist_required': row[2]
                }
                for row in tier_coverage
            ]

            # Completeness checks
            total_climate_zones = len(basix_coverage)
            total_dev_types = sum(row[1] for row in basix_coverage)
            total_registry_provisions = sum(row[1] for row in tier_coverage)

            completeness_score = 0
            if total_climate_zones >= 3:  # At least 3 climate zones
                completeness_score += 25
            if total_dev_types >= 15:     # At least 15 zone/dev-type combinations
                completeness_score += 25
            if total_registry_provisions >= 8:  # At least 8 provision types
                completeness_score += 25
            if len(tier_coverage) >= 2:  # At least 2 tier levels
                completeness_score += 25

            test_result['details']['completeness_score'] = completeness_score
            test_result['passed'] = completeness_score >= 75

            conn.close()

            if test_result['passed']:
                print(f"✅ Data Completeness: {completeness_score}% complete")
            else:
                print(f"❌ Data Completeness: Only {completeness_score}% complete (need 75%+)")

        except Exception as e:
            test_result['error'] = str(e)
            print(f"❌ Data Completeness verification failed: {e}")

        return test_result

    def run_all_tests(self) -> Dict:
        """Run all verification tests for PRP-Q1"""
        print("=" * 60)
        print("PRP-Q1 BASIX Integration Verification")
        print("=" * 60)

        tests = [
            self.verify_basix_schema(),
            self.verify_special_provisions_schema(),
            self.verify_basix_service(),
            self.verify_api_integration(),
            self.verify_data_completeness()
        ]

        # Store test results
        for test in tests:
            test_name = test['test']
            self.results['tests'][test_name] = test

        # Calculate summary
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t['passed'])
        success_rate = (passed_tests / total_tests) * 100

        self.results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': round(success_rate, 2),
            'verification_passed': success_rate >= 80
        }

        # Print summary
        print("\n" + "=" * 60)
        print(f"PRP-Q1 VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")

        if self.results['summary']['verification_passed']:
            print("✅ PRP-Q1 BASIX INTEGRATION VERIFIED SUCCESSFULLY")
            print("\nImplemented Features:")
            print("• BASIX provisions database with climate zone targeting")
            print("• Special provisions registry with tier assignments")
            print("• BASIX compliance checker service")
            print("• Enhanced compliance API with BASIX integration")
            print("• Comprehensive data coverage across multiple zones")
        else:
            print("❌ PRP-Q1 VERIFICATION FAILED")
            print("\nFailed Tests:")
            for test in tests:
                if not test['passed']:
                    error_msg = test.get('error', 'Test conditions not met')
                    print(f"• {test['test']}: {error_msg}")

        # Save detailed results
        with open('PRP_Q1_BASIX_VERIFICATION_REPORT.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nDetailed report: PRP_Q1_BASIX_VERIFICATION_REPORT.json")

        return self.results

if __name__ == "__main__":
    verifier = PRPQ1Verifier()
    verification_results = verifier.run_all_tests()

    # Exit with appropriate code
    if verification_results['summary']['verification_passed']:
        print("\n🎯 PRP-Q1 READY FOR PRODUCTION")
        sys.exit(0)
    else:
        print("\n🛑 PRP-Q1 VERIFICATION FAILED - Fix issues before proceeding")
        sys.exit(1)