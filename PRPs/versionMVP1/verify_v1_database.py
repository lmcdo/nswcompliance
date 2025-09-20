#!/usr/bin/env python3
"""
Verification script for PRP-V1: Database Foundation
Validates that all database objects were created correctly
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

class DatabaseVerification:
    """Verify database schema for version management"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "V1_DATABASE_FOUNDATION",
            "checks": {},
            "errors": [],
            "warnings": []
        }

    def check_schema_exists(self) -> bool:
        """Check if versions schema exists"""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = 'versions'
            """)
            exists = cursor.fetchone() is not None
            self.results["checks"]["schema_exists"] = exists
            return exists

    def check_tables_exist(self) -> Dict[str, bool]:
        """Check if all required tables exist"""
        required_tables = [
            ('versions', 'document_versions'),
            ('versions', 'version_audit_log')
        ]

        table_checks = {}
        with self.conn.cursor() as cursor:
            for schema, table in required_tables:
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                """, (schema, table))

                exists = cursor.fetchone() is not None
                table_checks[f"{schema}.{table}"] = exists

                if not exists:
                    self.results["errors"].append(f"Table {schema}.{table} not found")

        self.results["checks"]["tables"] = table_checks
        return table_checks

    def check_columns_added(self) -> Dict[str, bool]:
        """Check if version columns were added to existing tables"""
        tables_to_check = [
            ('public', 'regulatory_provisions', ['version_id', 'is_current', 'version_effective_date']),
            ('public', 'development_controls', ['version_id', 'is_current']),
            ('public', 'quantitative_standards', ['version_id', 'is_current'])
        ]

        column_checks = {}
        with self.conn.cursor() as cursor:
            for schema, table, columns in tables_to_check:
                for column in columns:
                    cursor.execute("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema = %s
                          AND table_name = %s
                          AND column_name = %s
                    """, (schema, table, column))

                    exists = cursor.fetchone() is not None
                    column_checks[f"{table}.{column}"] = exists

                    if not exists:
                        self.results["errors"].append(f"Column {column} not found in {table}")

        self.results["checks"]["columns"] = column_checks
        return column_checks

    def check_indexes(self) -> Dict[str, bool]:
        """Check if required indexes exist"""
        required_indexes = [
            'idx_version_lookup',
            'idx_version_dates',
            'idx_version_current',
            'idx_provisions_version',
            'idx_controls_version',
            'idx_standards_version'
        ]

        index_checks = {}
        with self.conn.cursor() as cursor:
            for index_name in required_indexes:
                cursor.execute("""
                    SELECT indexname
                    FROM pg_indexes
                    WHERE indexname = %s
                """, (index_name,))

                exists = cursor.fetchone() is not None
                index_checks[index_name] = exists

                if not exists:
                    self.results["warnings"].append(f"Index {index_name} not found")

        self.results["checks"]["indexes"] = index_checks
        return index_checks

    def check_functions(self) -> Dict[str, bool]:
        """Check if helper functions exist"""
        required_functions = [
            ('versions', 'get_current_version'),
            ('versions', 'get_version_at_date'),
            ('versions', 'log_version_change')
        ]

        function_checks = {}
        with self.conn.cursor() as cursor:
            for schema, function in required_functions:
                cursor.execute("""
                    SELECT routine_name
                    FROM information_schema.routines
                    WHERE routine_schema = %s
                      AND routine_name = %s
                """, (schema, function))

                exists = cursor.fetchone() is not None
                function_checks[f"{schema}.{function}"] = exists

                if not exists:
                    self.results["errors"].append(f"Function {schema}.{function} not found")

        self.results["checks"]["functions"] = function_checks
        return function_checks

    def check_constraints(self) -> Dict[str, bool]:
        """Check if constraints are properly configured"""
        constraint_checks = {}

        with self.conn.cursor() as cursor:
            # Check unique constraint on document_versions
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_schema = 'versions'
                  AND table_name = 'document_versions'
                  AND constraint_type = 'UNIQUE'
            """)

            unique_exists = cursor.fetchone() is not None
            constraint_checks['unique_version'] = unique_exists

            # Check foreign key constraints
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name IN ('regulatory_provisions', 'development_controls')
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'version_id'
            """)

            fk_count = cursor.fetchone()[0]
            constraint_checks['foreign_keys'] = fk_count >= 2

        self.results["checks"]["constraints"] = constraint_checks
        return constraint_checks

    def test_basic_operations(self) -> Dict[str, bool]:
        """Test basic database operations"""
        test_results = {}

        try:
            with self.conn.cursor() as cursor:
                # Test insert into document_versions
                cursor.execute("""
                    INSERT INTO versions.document_versions
                    (document_type, document_identifier, version_number, version_status,
                     effective_date, created_by)
                    VALUES ('SEPP', 'TEST-DOC-001', 'v0.1', 'CURRENT', CURRENT_DATE, 'test_script')
                    RETURNING id
                """)
                test_id = cursor.fetchone()[0]
                test_results['insert_version'] = True

                # Test function call
                cursor.execute("""
                    SELECT versions.get_current_version('SEPP', 'TEST-DOC-001')
                """)
                result = cursor.fetchone()
                test_results['function_call'] = result is not None

                # Clean up test data (delete audit log entries first)
                cursor.execute("""
                    DELETE FROM versions.version_audit_log
                    WHERE version_id = %s
                """, (test_id,))
                cursor.execute("""
                    DELETE FROM versions.document_versions
                    WHERE id = %s
                """, (test_id,))

                # Rollback to avoid committing test data
                self.conn.rollback()

        except Exception as e:
            self.results["errors"].append(f"Test operation failed: {str(e)}")
            test_results['operations'] = False
            self.conn.rollback()

        self.results["checks"]["test_operations"] = test_results
        return test_results

    def run_verification(self) -> bool:
        """Run all verification checks"""
        print("Verifying PRP-V1: Database Foundation...")

        # Run all checks
        self.check_schema_exists()
        self.check_tables_exist()
        self.check_columns_added()
        self.check_indexes()
        self.check_functions()
        self.check_constraints()
        self.test_basic_operations()

        # Determine overall success
        all_checks_passed = (
            len(self.results["errors"]) == 0 and
            all(self.results["checks"]["tables"].values()) and
            all(self.results["checks"]["columns"].values()) and
            all(self.results["checks"]["functions"].values())
        )

        self.results["success"] = all_checks_passed
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "passed": all_checks_passed
        }

        # Save results
        with open("verify_v1_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\nVerification Results:")
        print(f"  Schema exists: {self.results['checks'].get('schema_exists', False)}")
        print(f"  Tables created: {all(self.results['checks'].get('tables', {}).values())}")
        print(f"  Columns added: {all(self.results['checks'].get('columns', {}).values())}")
        print(f"  Functions created: {all(self.results['checks'].get('functions', {}).values())}")

        if self.results["errors"]:
            print("\nErrors found:")
            for error in self.results["errors"]:
                print(f"    - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"    - {warning}")

        print(f"\n{'VERIFICATION PASSED' if all_checks_passed else 'VERIFICATION FAILED'}")

        return all_checks_passed

if __name__ == "__main__":
    verifier = DatabaseVerification()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)