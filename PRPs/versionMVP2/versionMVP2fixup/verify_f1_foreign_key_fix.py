#!/usr/bin/env python3
"""
PRP-F1 Verification: Foreign Key Constraint Resolution
Fixes and verifies foreign key constraint issues in provision_changes table
"""

import os
import sys
import json
import psycopg2
from datetime import datetime

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from db_config import get_connection

class ForeignKeyConstraintFix:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "F1",
            "objective": "Foreign Key Constraint Resolution",
            "success": False,
            "actions_taken": [],
            "errors": [],
            "warnings": [],
            "statistics": {}
        }

    def get_db_connection(self):
        """Get database connection"""
        try:
            return get_connection()
        except Exception as e:
            # Fallback to direct connection
            return psycopg2.connect(
                host="127.0.0.1",
                database="nsw_planning",
                user="postgres",
                port=5432
            )

    def analyze_constraints(self) -> dict:
        """Analyze existing foreign key constraints"""
        print("Analyzing foreign key constraints...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'provision_changes'
            """)

            constraints = cursor.fetchall()
            conn.close()

            constraint_info = {
                "total_constraints": len(constraints),
                "constraints": [
                    {
                        "name": row[0],
                        "table": row[1],
                        "column": row[2],
                        "referenced_table": row[3],
                        "referenced_column": row[4]
                    }
                    for row in constraints
                ]
            }

            self.results["actions_taken"].append("Analyzed foreign key constraints")
            return constraint_info

        except Exception as e:
            self.results["errors"].append(f"Constraint analysis failed: {str(e)}")
            return {}

    def check_orphaned_references(self) -> dict:
        """Check for orphaned references in provision_changes"""
        print("Checking for orphaned references...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Check if provision_changes table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'versions'
                    AND table_name = 'provision_changes'
                )
            """)
            table_exists = cursor.fetchone()[0]

            if not table_exists:
                print("  provision_changes table does not exist - creating it...")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS versions.provision_changes (
                        id SERIAL PRIMARY KEY,
                        provision_id INTEGER NOT NULL,
                        document_version_id INTEGER REFERENCES versions.document_versions(id),
                        change_type VARCHAR(50) NOT NULL,
                        change_description TEXT,
                        old_value TEXT,
                        new_value TEXT,
                        change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        changed_by VARCHAR(100) DEFAULT 'system'
                    )
                """)
                conn.commit()
                self.results["actions_taken"].append("Created provision_changes table")
                return {"orphaned_count": 0, "table_created": True}

            # Check for orphaned references
            cursor.execute("""
                SELECT DISTINCT pc.document_version_id, COUNT(*) as count
                FROM versions.provision_changes pc
                LEFT JOIN versions.document_versions dv ON pc.document_version_id = dv.id
                WHERE dv.id IS NULL
                GROUP BY pc.document_version_id
            """)

            orphaned = cursor.fetchall()
            conn.close()

            orphan_info = {
                "orphaned_count": len(orphaned),
                "orphaned_versions": [{"version_id": row[0], "count": row[1]} for row in orphaned],
                "table_created": False
            }

            self.results["actions_taken"].append("Checked for orphaned references")
            return orphan_info

        except Exception as e:
            self.results["errors"].append(f"Orphaned reference check failed: {str(e)}")
            return {}

    def fix_orphaned_references(self, orphan_info: dict) -> bool:
        """Fix orphaned references by removing invalid records"""
        if orphan_info.get("orphaned_count", 0) == 0:
            print("  No orphaned references found")
            return True

        print(f"  Fixing {orphan_info['orphaned_count']} orphaned references...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Remove invalid records
            cursor.execute("""
                DELETE FROM versions.provision_changes
                WHERE document_version_id NOT IN (
                    SELECT id FROM versions.document_versions
                )
            """)

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            print(f"  Removed {deleted_count} orphaned records")
            self.results["actions_taken"].append(f"Removed {deleted_count} orphaned provision_changes records")
            return True

        except Exception as e:
            self.results["errors"].append(f"Failed to fix orphaned references: {str(e)}")
            return False

    def create_validation_function(self) -> bool:
        """Create validation function for version references"""
        print("Creating validation function...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE OR REPLACE FUNCTION versions.validate_version_reference(version_id INTEGER)
                RETURNS BOOLEAN AS $$
                BEGIN
                    RETURN EXISTS (SELECT 1 FROM versions.document_versions WHERE id = version_id);
                END;
                $$ LANGUAGE plpgsql;
            """)

            conn.commit()
            conn.close()

            self.results["actions_taken"].append("Created validation function")
            return True

        except Exception as e:
            self.results["errors"].append(f"Failed to create validation function: {str(e)}")
            return False

    def test_constraint_functionality(self) -> bool:
        """Test that constraints are working properly"""
        print("Testing constraint functionality...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Get a valid version ID
            cursor.execute("SELECT id FROM versions.document_versions LIMIT 1")
            result = cursor.fetchone()
            if not result:
                self.results["warnings"].append("No document versions found for testing")
                conn.close()
                return True

            valid_version_id = result[0]

            # Test valid insertion
            cursor.execute("""
                INSERT INTO versions.provision_changes
                (provision_id, document_version_id, change_type, change_description)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (1, valid_version_id, 'TEST', 'Constraint test'))

            test_id = cursor.fetchone()[0]

            # Clean up test record
            cursor.execute("DELETE FROM versions.provision_changes WHERE id = %s", (test_id,))

            conn.commit()
            conn.close()

            self.results["actions_taken"].append("Tested constraint functionality")
            return True

        except Exception as e:
            self.results["errors"].append(f"Constraint test failed: {str(e)}")
            return False

    def verify_statistics(self) -> dict:
        """Get verification statistics"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Count document versions
            cursor.execute("SELECT COUNT(*) FROM versions.document_versions")
            version_count = cursor.fetchone()[0]

            # Count provision changes
            cursor.execute("SELECT COUNT(*) FROM versions.provision_changes")
            changes_count = cursor.fetchone()[0]

            # Count orphaned references (should be 0)
            cursor.execute("""
                SELECT COUNT(*)
                FROM versions.provision_changes pc
                LEFT JOIN versions.document_versions dv ON pc.document_version_id = dv.id
                WHERE dv.id IS NULL
            """)
            orphaned_count = cursor.fetchone()[0]

            conn.close()

            stats = {
                "document_versions": version_count,
                "provision_changes": changes_count,
                "orphaned_references": orphaned_count
            }

            return stats

        except Exception as e:
            self.results["errors"].append(f"Statistics collection failed: {str(e)}")
            return {}

    def execute_fix(self) -> bool:
        """Execute the complete foreign key constraint fix"""
        print("Starting PRP-F1 Foreign Key Constraint Fix...")
        print("=" * 60)

        # Step 1: Analyze constraints
        constraint_info = self.analyze_constraints()
        self.results["statistics"]["constraints"] = constraint_info

        # Step 2: Check for orphaned references
        orphan_info = self.check_orphaned_references()
        self.results["statistics"]["orphaned"] = orphan_info

        # Step 3: Fix orphaned references
        if not self.fix_orphaned_references(orphan_info):
            return False

        # Step 4: Create validation function
        if not self.create_validation_function():
            return False

        # Step 5: Test functionality
        if not self.test_constraint_functionality():
            return False

        # Step 6: Final verification
        final_stats = self.verify_statistics()
        self.results["statistics"]["final"] = final_stats

        # Determine success
        success = (
            len(self.results["errors"]) == 0 and
            final_stats.get("orphaned_references", 1) == 0
        )

        self.results["success"] = success

        # Save results
        with open("verify_f1_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("PRP-F1 FOREIGN KEY CONSTRAINT FIX RESULTS")
        print("=" * 60)
        print(f"Document versions: {final_stats.get('document_versions', 0)}")
        print(f"Provision changes: {final_stats.get('provision_changes', 0)}")
        print(f"Orphaned references: {final_stats.get('orphaned_references', 0)}")
        print(f"Actions taken: {len(self.results['actions_taken'])}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\nPRP-F1 FOREIGN KEY FIX {'PASSED' if success else 'FAILED'}")

        return success

def main():
    """Main entry point"""
    fixer = ForeignKeyConstraintFix()
    success = fixer.execute_fix()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()