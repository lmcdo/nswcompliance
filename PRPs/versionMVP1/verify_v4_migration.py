#!/usr/bin/env python3
"""
Verification script for PRP-V4: Data Migration
Validates that existing data was successfully migrated to versioned schema
"""

import sys
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from db_config import get_connection
from psycopg2.extras import RealDictCursor

class MigrationVerification:
    """Verify data migration to versioned schema"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "V4_DATA_MIGRATION",
            "checks": {},
            "errors": [],
            "warnings": [],
            "statistics": {},
            "success": False
        }

    def check_version_records_created(self) -> Dict[str, int]:
        """Check that version records were created for all documents"""
        stats = {}

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Count total unique documents
            cursor.execute("""
                SELECT COUNT(DISTINCT document_id) as total_documents
                FROM regulatory_provisions
                WHERE document_id IS NOT NULL
            """)
            stats['total_documents'] = cursor.fetchone()['total_documents']

            # Count version records
            cursor.execute("""
                SELECT
                    document_type,
                    COUNT(*) as count,
                    COUNT(CASE WHEN version_status = 'CURRENT' THEN 1 END) as current_count
                FROM versions.document_versions
                GROUP BY document_type
            """)
            version_counts = cursor.fetchall()

            stats['versions_by_type'] = {
                row['document_type']: {
                    'total': row['count'],
                    'current': row['current_count']
                }
                for row in version_counts
            }

            # Total version records
            stats['total_versions'] = sum(
                v['total'] for v in stats['versions_by_type'].values()
            )

            # Check if counts match
            stats['documents_match_versions'] = (
                stats['total_documents'] == stats['total_versions']
            )

        return stats

    def check_provisions_linked(self) -> Dict[str, any]:
        """Check that provisions are linked to versions"""
        link_stats = {}

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Count total provisions
            cursor.execute("SELECT COUNT(*) as total FROM regulatory_provisions")
            link_stats['total_provisions'] = cursor.fetchone()['total']

            # Count provisions with version_id
            cursor.execute("""
                SELECT COUNT(*) as linked
                FROM regulatory_provisions
                WHERE version_id IS NOT NULL
            """)
            link_stats['linked_provisions'] = cursor.fetchone()['linked']

            # Count provisions without version_id
            cursor.execute("""
                SELECT COUNT(*) as unlinked
                FROM regulatory_provisions
                WHERE version_id IS NULL AND document_id IS NOT NULL
            """)
            link_stats['unlinked_provisions'] = cursor.fetchone()['unlinked']

            # Calculate percentage
            if link_stats['total_provisions'] > 0:
                link_stats['link_percentage'] = (
                    link_stats['linked_provisions'] / link_stats['total_provisions'] * 100
                )
            else:
                link_stats['link_percentage'] = 0

            # Check is_current flag
            cursor.execute("""
                SELECT
                    COUNT(*) as total_current,
                    COUNT(CASE WHEN version_id IS NOT NULL THEN 1 END) as current_with_version
                FROM regulatory_provisions
                WHERE is_current = true
            """)
            current_stats = cursor.fetchone()
            link_stats['current_provisions'] = current_stats['total_current']
            link_stats['current_with_version'] = current_stats['current_with_version']

            # Get sample of unlinked documents
            if link_stats['unlinked_provisions'] > 0:
                cursor.execute("""
                    SELECT DISTINCT document_id
                    FROM regulatory_provisions
                    WHERE version_id IS NULL AND document_id IS NOT NULL
                    LIMIT 5
                """)
                link_stats['sample_unlinked'] = [row['document_id'] for row in cursor.fetchall()]

        return link_stats

    def check_data_integrity(self) -> Dict[str, bool]:
        """Verify data integrity after migration"""
        integrity_checks = {}

        with self.conn.cursor() as cursor:
            # Check for orphaned version references
            cursor.execute("""
                SELECT COUNT(*) FROM regulatory_provisions rp
                WHERE rp.version_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM versions.document_versions dv
                      WHERE dv.id = rp.version_id
                  )
            """)
            orphaned_count = cursor.fetchone()[0]
            integrity_checks['no_orphaned_versions'] = orphaned_count == 0

            # Check for duplicate current versions
            cursor.execute("""
                SELECT document_identifier, COUNT(*) as count
                FROM versions.document_versions
                WHERE version_status = 'CURRENT'
                GROUP BY document_identifier
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            integrity_checks['no_duplicate_current'] = len(duplicates) == 0

            if duplicates:
                self.results["errors"].append(f"Duplicate current versions found: {duplicates}")

            # Check version status consistency
            cursor.execute("""
                SELECT COUNT(*) FROM versions.document_versions
                WHERE version_status NOT IN ('CURRENT', 'PREVIOUS', 'ARCHIVED')
            """)
            invalid_status = cursor.fetchone()[0]
            integrity_checks['valid_status_values'] = invalid_status == 0

            # Check date consistency
            cursor.execute("""
                SELECT COUNT(*) FROM versions.document_versions
                WHERE superseded_date IS NOT NULL
                  AND superseded_date < effective_date
            """)
            invalid_dates = cursor.fetchone()[0]
            integrity_checks['valid_date_ranges'] = invalid_dates == 0

        return integrity_checks

    def check_related_tables(self) -> Dict[str, Dict]:
        """Check that related tables were also migrated"""
        related_stats = {}

        tables_to_check = [
            'development_controls',
            'quantitative_standards'
        ]

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            for table in tables_to_check:
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total,
                        COUNT(version_id) as with_version,
                        COUNT(CASE WHEN is_current = true THEN 1 END) as current
                    FROM {table}
                """)
                stats = cursor.fetchone()
                related_stats[table] = dict(stats)

                # Calculate percentage
                if stats['total'] > 0:
                    related_stats[table]['version_percentage'] = (
                        stats['with_version'] / stats['total'] * 100
                    )

        return related_stats

    def validate_version_functions(self) -> Dict[str, bool]:
        """Test that version functions work correctly"""
        function_tests = {}

        with self.conn.cursor() as cursor:
            try:
                # Test get_current_version function
                cursor.execute("""
                    SELECT versions.get_current_version('LEP', 'Inner-West-LEP-2022')
                """)
                result = cursor.fetchone()
                function_tests['get_current_version'] = True
            except Exception as e:
                function_tests['get_current_version'] = False
                self.results["errors"].append(f"Function test failed: {str(e)}")

            try:
                # Test get_version_at_date function
                cursor.execute("""
                    SELECT versions.get_version_at_date('LEP', 'Inner-West-LEP-2022', CURRENT_DATE)
                """)
                result = cursor.fetchone()
                function_tests['get_version_at_date'] = True
            except Exception as e:
                function_tests['get_version_at_date'] = False
                self.results["errors"].append(f"Function test failed: {str(e)}")

        return function_tests

    def check_audit_log(self) -> Dict[str, any]:
        """Check that audit log is capturing changes"""
        audit_stats = {}

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Count audit entries
            cursor.execute("""
                SELECT
                    COUNT(*) as total_entries,
                    COUNT(DISTINCT version_id) as unique_versions,
                    MIN(performed_at) as earliest_entry,
                    MAX(performed_at) as latest_entry
                FROM versions.version_audit_log
            """)
            stats = cursor.fetchone()
            audit_stats.update(dict(stats))

            # Check if audit trigger is working
            audit_stats['audit_enabled'] = stats['total_entries'] > 0

        return audit_stats

    def run_verification(self) -> bool:
        """Run all migration verification checks"""
        print("🔍 Verifying PRP-V4: Data Migration...")

        # Check version records
        print("\n📊 Checking version records...")
        version_stats = self.check_version_records_created()
        self.results["statistics"]["versions"] = version_stats
        print(f"  Documents: {version_stats['total_documents']}")
        print(f"  Version records: {version_stats['total_versions']}")
        print(f"  Match: {'✅' if version_stats['documents_match_versions'] else '❌'}")

        # Check provision linking
        print("\n🔗 Checking provision linking...")
        link_stats = self.check_provisions_linked()
        self.results["statistics"]["linking"] = link_stats
        print(f"  Total provisions: {link_stats['total_provisions']}")
        print(f"  Linked provisions: {link_stats['linked_provisions']}")
        print(f"  Link percentage: {link_stats['link_percentage']:.1f}%")

        if link_stats['unlinked_provisions'] > 0:
            self.results["warnings"].append(
                f"{link_stats['unlinked_provisions']} provisions not linked to versions"
            )

        # Check data integrity
        print("\n🔒 Checking data integrity...")
        integrity = self.check_data_integrity()
        self.results["checks"]["integrity"] = integrity
        print(f"  No orphaned versions: {'✅' if integrity['no_orphaned_versions'] else '❌'}")
        print(f"  No duplicate current: {'✅' if integrity['no_duplicate_current'] else '❌'}")
        print(f"  Valid status values: {'✅' if integrity['valid_status_values'] else '❌'}")

        # Check related tables
        print("\n📋 Checking related tables...")
        related = self.check_related_tables()
        self.results["statistics"]["related_tables"] = related
        for table, stats in related.items():
            print(f"  {table}: {stats.get('version_percentage', 0):.1f}% versioned")

        # Test version functions
        print("\n🧪 Testing version functions...")
        functions = self.validate_version_functions()
        self.results["checks"]["functions"] = functions
        print(f"  Functions operational: {'✅' if all(functions.values()) else '❌'}")

        # Check audit log
        print("\n📝 Checking audit log...")
        audit = self.check_audit_log()
        self.results["statistics"]["audit"] = audit
        print(f"  Audit entries: {audit['total_entries']}")
        print(f"  Audit enabled: {'✅' if audit['audit_enabled'] else '❌'}")

        # Determine overall success
        critical_checks_passed = (
            version_stats['total_versions'] > 0 and
            link_stats['link_percentage'] >= 95.0 and  # Allow 5% margin
            all(integrity.values()) and
            all(functions.values())
        )

        self.results["success"] = critical_checks_passed

        # Save results
        with open("verify_v4_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        # Print summary
        print("\n" + "=" * 50)
        print("📊 Migration Verification Summary:")
        print(f"  Version records created: {'✅' if version_stats['total_versions'] > 0 else '❌'}")
        print(f"  Provisions linked: {'✅' if link_stats['link_percentage'] >= 95 else '❌'} ({link_stats['link_percentage']:.1f}%)")
        print(f"  Data integrity: {'✅' if all(integrity.values()) else '❌'}")
        print(f"  Functions working: {'✅' if all(functions.values()) else '❌'}")

        if self.results["errors"]:
            print("\n❌ Errors found:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\n{'✅ PRP-V4 VERIFICATION PASSED' if critical_checks_passed else '❌ PRP-V4 VERIFICATION FAILED'}")

        return critical_checks_passed

def main():
    """Main entry point"""
    verifier = MigrationVerification()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()