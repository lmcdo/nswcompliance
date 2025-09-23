#!/usr/bin/env python3
"""
GRANULAR Verification script for PRP-V5-Enhanced: Provision Change Tracking
- Verifies every database modification individually
- Tests every service method separately
- Validates all code changes with specific checks
- Provides detailed failure analysis for each component
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection
import json
from datetime import datetime, date
from typing import Dict, List, Tuple
import importlib.util

class PRPV5EnhancedVerification:
    """Granular verification for every aspect of PRP-V5-Enhanced"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-V5-ENHANCED_PROVISION_CHANGE_TRACKING",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "warnings": []
        }

    def verify_database_schema_changes(self) -> Dict[str, bool]:
        """Verify each database modification individually"""
        print("Verifying database schema changes...")

        schema_checks = {}
        with self.conn.cursor() as cursor:
            try:
                # Check 1: provision_changes table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_schema = 'versions'
                        AND table_name = 'provision_changes'
                    )
                """)
                schema_checks['provision_changes_table_exists'] = cursor.fetchone()[0]

                if schema_checks['provision_changes_table_exists']:
                    # Check 2: All required columns exist
                    cursor.execute("""
                        SELECT column_name FROM information_schema.columns
                        WHERE table_schema = 'versions'
                        AND table_name = 'provision_changes'
                        ORDER BY column_name
                    """)
                    columns = [row[0] for row in cursor.fetchall()]
                    required_columns = [
                        'id', 'document_version_id', 'provision_id', 'change_type',
                        'old_content', 'new_content', 'change_summary', 'change_metadata',
                        'effective_date', 'created_at', 'created_by'
                    ]

                    for col in required_columns:
                        schema_checks[f'column_{col}_exists'] = col in columns

                    # Check 3: change_type constraint exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.check_constraints cc
                        JOIN information_schema.constraint_column_usage ccu
                            ON cc.constraint_name = ccu.constraint_name
                        WHERE ccu.table_schema = 'versions'
                        AND ccu.table_name = 'provision_changes'
                        AND ccu.column_name = 'change_type'
                    """)
                    schema_checks['change_type_constraint_exists'] = cursor.fetchone()[0] > 0

                    # Check 4: Foreign key constraints exist
                    cursor.execute("""
                        SELECT COUNT(*) FROM information_schema.table_constraints
                        WHERE table_schema = 'versions'
                        AND table_name = 'provision_changes'
                        AND constraint_type = 'FOREIGN KEY'
                    """)
                    schema_checks['foreign_keys_exist'] = cursor.fetchone()[0] >= 2

                    # Check 5: Performance indexes exist
                    cursor.execute("""
                        SELECT indexname FROM pg_indexes
                        WHERE tablename = 'provision_changes'
                        AND schemaname = 'versions'
                        ORDER BY indexname
                    """)
                    indexes = [row[0] for row in cursor.fetchall()]
                    expected_indexes = [
                        'idx_provision_changes_provision',
                        'idx_provision_changes_document_version',
                        'idx_provision_changes_type_date'
                    ]

                    for idx in expected_indexes:
                        schema_checks[f'index_{idx}_exists'] = idx in indexes

                else:
                    # Table doesn't exist - mark all dependent checks as failed
                    schema_checks['provision_changes_table_missing'] = True

            except Exception as e:
                self.results["errors"].append(f"Database schema verification failed: {str(e)}")
                schema_checks['verification_error'] = str(e)

        self.results["checks"]["database_schema"] = schema_checks
        return schema_checks

    def verify_change_detection_functions(self) -> Dict[str, bool]:
        """Verify change detection algorithm functionality"""
        print("Verifying change detection functions...")

        detection_checks = {}

        try:
            # Check if enhanced VersionManager exists and has new methods
            from services.version_manager import VersionManager

            vm = VersionManager()
            detection_checks['version_manager_imports'] = True

            # Check 1: detect_provision_changes method exists
            detection_checks['detect_provision_changes_method'] = hasattr(vm, 'detect_provision_changes')

            # Check 2: generate_change_summary method exists
            detection_checks['generate_change_summary_method'] = hasattr(vm, 'generate_change_summary')

            # Check 3: create_new_version_with_change_tracking method exists
            detection_checks['create_with_tracking_method'] = hasattr(vm, 'create_new_version_with_change_tracking')

            # Check 4: record_provision_changes method exists
            detection_checks['record_changes_method'] = hasattr(vm, 'record_provision_changes')

            # Test change detection with sample data
            if detection_checks.get('detect_provision_changes_method', False):
                old_provisions = [
                    {'ref_number': '4.1', 'provision_text': 'Maximum height: 9m'},
                    {'ref_number': '4.2', 'provision_text': 'Front setback: 6m'}
                ]
                new_provisions = [
                    {'ref_number': '4.1', 'provision_text': 'Maximum height: 12m'},
                    {'ref_number': '4.3', 'provision_text': 'Side setback: 1.5m'}
                ]

                try:
                    changes = vm.detect_provision_changes(old_provisions, new_provisions)
                    detection_checks['change_detection_functional'] = len(changes) > 0
                    detection_checks['detects_modifications'] = any(c['change_type'] == 'MODIFIED' for c in changes)
                    detection_checks['detects_deletions'] = any(c['change_type'] == 'DELETED' for c in changes)
                    detection_checks['detects_new_provisions'] = any(c['change_type'] == 'NEW' for c in changes)
                except Exception as e:
                    detection_checks['change_detection_error'] = str(e)

            vm.close()

        except ImportError as e:
            detection_checks['import_error'] = str(e)
            self.results["errors"].append(f"Cannot import enhanced VersionManager: {str(e)}")
        except Exception as e:
            detection_checks['general_error'] = str(e)
            self.results["errors"].append(f"Change detection verification failed: {str(e)}")

        self.results["checks"]["change_detection"] = detection_checks
        return detection_checks

    def verify_change_summary_generation(self) -> Dict[str, bool]:
        """Verify change summary generation accuracy"""
        print("Verifying change summary generation...")

        summary_checks = {}

        try:
            from services.version_manager import VersionManager
            vm = VersionManager()

            # Test height change detection
            if hasattr(vm, 'extract_height_change'):
                old_text = "maximum height of 9 metres"
                new_text = "maximum height of 12 metres"
                height_summary = vm.extract_height_change(old_text, new_text)
                summary_checks['height_change_detection'] = height_summary is not None
                summary_checks['height_change_accurate'] = "9" in str(height_summary) and "12" in str(height_summary)

            # Test setback change detection
            if hasattr(vm, 'extract_setback_change'):
                old_text = "front setback of 6 metres"
                new_text = "front setback of 4.5 metres"
                setback_summary = vm.extract_setback_change(old_text, new_text)
                summary_checks['setback_change_detection'] = setback_summary is not None

            # Test generic change summary
            if hasattr(vm, 'generate_change_summary'):
                old_provision = {'provision_text': 'Short text'}
                new_provision = {'provision_text': 'This is a much longer text with additional requirements and conditions'}
                summary = vm.generate_change_summary(old_provision, new_provision)
                summary_checks['generic_summary_generation'] = len(summary) > 0
                summary_checks['expansion_detection'] = 'expand' in summary.lower()

            vm.close()

        except Exception as e:
            summary_checks['summary_generation_error'] = str(e)
            self.results["errors"].append(f"Summary generation verification failed: {str(e)}")

        self.results["checks"]["summary_generation"] = summary_checks
        return summary_checks

    def verify_change_recording_functionality(self) -> Dict[str, bool]:
        """Verify change recording and storage"""
        print("Verifying change recording functionality...")

        recording_checks = {}

        try:
            with self.conn.cursor() as cursor:
                # Check 1: Can insert test change record
                test_change = {
                    'document_version_id': 1,  # Assuming at least one version exists
                    'provision_id': None,
                    'change_type': 'MODIFIED',
                    'old_content': 'Test old content',
                    'new_content': 'Test new content',
                    'change_summary': 'Test change summary',
                    'change_metadata': '{}',
                    'effective_date': '2024-09-20',
                    'created_by': 'test_script'
                }

                cursor.execute("""
                    INSERT INTO versions.provision_changes (
                        document_version_id, provision_id, change_type,
                        old_content, new_content, change_summary,
                        change_metadata, effective_date, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    test_change['document_version_id'],
                    test_change['provision_id'],
                    test_change['change_type'],
                    test_change['old_content'],
                    test_change['new_content'],
                    test_change['change_summary'],
                    test_change['change_metadata'],
                    test_change['effective_date'],
                    test_change['created_by']
                ))

                test_id = cursor.fetchone()[0]
                recording_checks['can_insert_changes'] = test_id is not None

                # Check 2: Can retrieve change record
                cursor.execute("""
                    SELECT change_type, change_summary FROM versions.provision_changes
                    WHERE id = %s
                """, (test_id,))
                retrieved = cursor.fetchone()
                recording_checks['can_retrieve_changes'] = retrieved is not None
                recording_checks['data_integrity'] = (
                    retrieved[0] == test_change['change_type'] and
                    retrieved[1] == test_change['change_summary']
                )

                # Check 3: Constraint validation works
                try:
                    cursor.execute("""
                        INSERT INTO versions.provision_changes (change_type)
                        VALUES ('INVALID_TYPE')
                    """)
                    recording_checks['constraint_validation'] = False
                except Exception:
                    recording_checks['constraint_validation'] = True

                # Clean up test data
                cursor.execute("DELETE FROM versions.provision_changes WHERE id = %s", (test_id,))
                self.conn.commit()

        except Exception as e:
            recording_checks['recording_error'] = str(e)
            self.results["errors"].append(f"Change recording verification failed: {str(e)}")
            self.conn.rollback()

        self.results["checks"]["change_recording"] = recording_checks
        return recording_checks

    def verify_change_query_methods(self) -> Dict[str, bool]:
        """Verify change history and analysis queries"""
        print("Verifying change query methods...")

        query_checks = {}

        try:
            from services.version_manager import VersionManager
            vm = VersionManager()

            # Check 1: get_version_changes method exists and works
            if hasattr(vm, 'get_version_changes'):
                changes = vm.get_version_changes('test_document', limit=10)
                query_checks['get_version_changes_method'] = True
                query_checks['get_version_changes_returns_list'] = isinstance(changes, list)

            # Check 2: get_provision_change_summary method exists and works
            if hasattr(vm, 'get_provision_change_summary'):
                summary = vm.get_provision_change_summary('test_document', 'v1.0', 'v1.1')
                query_checks['get_change_summary_method'] = True
                query_checks['get_change_summary_returns_dict'] = isinstance(summary, dict)

            # Check 3: Query performance (should be fast even with no data)
            start_time = datetime.now()
            if hasattr(vm, 'get_version_changes'):
                vm.get_version_changes('nonexistent_document')
            end_time = datetime.now()
            query_time_ms = (end_time - start_time).total_seconds() * 1000
            query_checks['query_performance_acceptable'] = query_time_ms < 1000  # Less than 1 second

            vm.close()

        except Exception as e:
            query_checks['query_methods_error'] = str(e)
            self.results["errors"].append(f"Change query verification failed: {str(e)}")

        self.results["checks"]["change_queries"] = query_checks
        return query_checks

    def verify_integration_compatibility(self) -> Dict[str, bool]:
        """Verify backward compatibility and integration"""
        print("Verifying integration compatibility...")

        integration_checks = {}

        try:
            from services.version_manager import VersionManager, DocumentType, VersionStatus

            # Check 1: Existing methods still work
            vm = VersionManager()

            # Test existing functionality
            version = vm.get_current_version(DocumentType.LEP, 'nonexistent_document')
            integration_checks['existing_get_current_works'] = True  # If no exception thrown

            stats = vm.get_version_statistics()
            integration_checks['existing_statistics_work'] = isinstance(stats, dict)

            # Check 2: Enhanced methods don't break existing functionality
            if hasattr(vm, 'create_new_version_with_change_tracking'):
                integration_checks['enhanced_methods_available'] = True
            else:
                integration_checks['enhanced_methods_available'] = False
                self.results["warnings"].append("Enhanced change tracking methods not implemented")

            # Check 3: Connection handling works properly
            vm.close()
            integration_checks['connection_management_works'] = True

        except Exception as e:
            integration_checks['integration_error'] = str(e)
            self.results["errors"].append(f"Integration compatibility verification failed: {str(e)}")

        self.results["checks"]["integration_compatibility"] = integration_checks
        return integration_checks

    def verify_performance_requirements(self) -> Dict[str, bool]:
        """Verify performance benchmarks are met"""
        print("Verifying performance requirements...")

        performance_checks = {}

        try:
            # Check database query performance
            with self.conn.cursor() as cursor:
                start_time = datetime.now()
                cursor.execute("""
                    SELECT COUNT(*) FROM versions.provision_changes
                    WHERE change_type = 'MODIFIED'
                    AND effective_date >= '2024-01-01'
                """)
                cursor.fetchone()
                end_time = datetime.now()

                query_time_ms = (end_time - start_time).total_seconds() * 1000
                performance_checks['change_query_under_1s'] = query_time_ms < 1000

                # Check index usage
                cursor.execute("""
                    EXPLAIN (FORMAT JSON)
                    SELECT * FROM versions.provision_changes
                    WHERE provision_id = 1
                """)
                plan = cursor.fetchone()[0]
                performance_checks['indexes_being_used'] = 'Index Scan' in str(plan)

        except Exception as e:
            performance_checks['performance_check_error'] = str(e)
            self.results["warnings"].append(f"Performance verification incomplete: {str(e)}")

        self.results["checks"]["performance"] = performance_checks
        return performance_checks

    def run_comprehensive_verification(self) -> bool:
        """Run all granular verification checks"""
        print("Starting PRP-V5-Enhanced Comprehensive Verification...")

        # Run all verification categories
        schema_results = self.verify_database_schema_changes()
        detection_results = self.verify_change_detection_functions()
        summary_results = self.verify_change_summary_generation()
        recording_results = self.verify_change_recording_functionality()
        query_results = self.verify_change_query_methods()
        integration_results = self.verify_integration_compatibility()
        performance_results = self.verify_performance_requirements()

        # Calculate success metrics
        all_checks = [
            schema_results, detection_results, summary_results,
            recording_results, query_results, integration_results, performance_results
        ]

        total_checks = sum(len(checks) for checks in all_checks)
        passed_checks = sum(
            sum(1 for result in checks.values() if result is True)
            for checks in all_checks
        )

        success_rate = passed_checks / total_checks if total_checks > 0 else 0

        # Determine overall success (require 90% pass rate)
        success = (
            len(self.results["errors"]) == 0 and
            success_rate >= 0.9 and
            schema_results.get('provision_changes_table_exists', False)
        )

        self.results["success"] = success
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "success_rate": success_rate,
            "critical_components_verified": {
                "database_schema": all(v for k, v in schema_results.items() if k.endswith('_exists')),
                "change_detection": detection_results.get('change_detection_functional', False),
                "change_recording": recording_results.get('can_insert_changes', False),
                "integration": integration_results.get('existing_get_current_works', False)
            }
        }

        # Save detailed results
        output_file = "verify_v5_enhanced_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print detailed summary
        print("\n" + "="*60)
        print("PRP-V5-ENHANCED GRANULAR VERIFICATION RESULTS")
        print("="*60)
        print(f"Total checks performed: {total_checks}")
        print(f"Checks passed: {passed_checks}")
        print(f"Success rate: {success_rate:.1%}")
        print(f"Errors: {len(self.results['errors'])}")
        print(f"Warnings: {len(self.results['warnings'])}")

        print(f"\nComponent Verification:")
        print(f"  Database Schema: {'PASS' if all(v for k, v in schema_results.items() if k.endswith('_exists')) else 'FAIL'}")
        print(f"  Change Detection: {'PASS' if detection_results.get('change_detection_functional', False) else 'FAIL'}")
        print(f"  Change Recording: {'PASS' if recording_results.get('can_insert_changes', False) else 'FAIL'}")
        print(f"  Query Methods: {'PASS' if query_results.get('get_version_changes_method', False) else 'FAIL'}")
        print(f"  Integration: {'PASS' if integration_results.get('existing_get_current_works', False) else 'FAIL'}")
        print(f"  Performance: {'PASS' if performance_results.get('change_query_under_1s', False) else 'FAIL'}")

        if self.results["errors"]:
            print(f"\nCritical Errors:")
            for error in self.results["errors"]:
                print(f"  ERROR: {error}")

        if self.results["warnings"]:
            print(f"\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  WARNING: {warning}")

        print(f"\n{'PRP-V5-ENHANCED VERIFICATION PASSED' if success else 'PRP-V5-ENHANCED VERIFICATION FAILED'}")
        print(f"Detailed results saved to: {output_file}")

        return success

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

if __name__ == "__main__":
    verifier = PRPV5EnhancedVerification()
    try:
        success = verifier.run_comprehensive_verification()
        sys.exit(0 if success else 1)
    finally:
        verifier.close()
