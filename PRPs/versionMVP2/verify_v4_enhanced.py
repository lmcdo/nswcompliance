#!/usr/bin/env python3
"""
AUTOCOMPLETE Verification script for PRP-V4-Enhanced: Data Migration with Baseline Versioning
- Checks current migration status
- Creates baseline versions if missing
- Links provisions to versions automatically
- Sets up change tracking infrastructure
- Provides complete verification results
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection
import json
from datetime import datetime, date
from typing import Dict, List, Tuple
import re

class PRPV4EnhancedVerification:
    """Autocomplete verification and implementation for PRP-V4-Enhanced"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-V4-ENHANCED_DATA_MIGRATION_BASELINE",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "warnings": []
        }
        self.baseline_date = '2024-09-20'

    def analyze_current_provisions(self) -> Dict[str, any]:
        """Analyze existing provisions for migration planning"""
        print("Analyzing current provisions...")

        analysis = {}
        with self.conn.cursor() as cursor:
            try:
                # Total provisions
                cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
                analysis['total_provisions'] = cursor.fetchone()[0]

                # Versioned vs unversioned
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(version_id) as versioned,
                        COUNT(*) - COUNT(version_id) as unversioned
                    FROM regulatory_provisions
                """)
                result = cursor.fetchone()
                analysis['versioning_status'] = {
                    'total': result[0],
                    'versioned': result[1],
                    'unversioned': result[2]
                }

                # Document type analysis
                cursor.execute("""
                    SELECT
                        CASE
                            WHEN document_id LIKE '%LEP%' THEN 'LEP'
                            WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
                            WHEN document_id LIKE '%DCP%' THEN 'DCP'
                            ELSE 'UNKNOWN'
                        END as document_type,
                        COUNT(*) as provision_count,
                        COUNT(DISTINCT regexp_replace(document_id, '_.*', '')) as unique_documents
                    FROM regulatory_provisions
                    WHERE document_id IS NOT NULL
                    GROUP BY document_type
                    ORDER BY provision_count DESC
                """)
                analysis['document_types'] = [
                    {'type': row[0], 'provisions': row[1], 'documents': row[2]}
                    for row in cursor.fetchall()
                ]

                # Sample documents
                cursor.execute("""
                    SELECT
                        regexp_replace(document_id, '_.*', '') as doc_identifier,
                        COUNT(*) as provision_count
                    FROM regulatory_provisions
                    WHERE document_id IS NOT NULL
                    GROUP BY doc_identifier
                    ORDER BY provision_count DESC
                    LIMIT 10
                """)
                analysis['top_documents'] = [
                    {'identifier': row[0], 'provisions': row[1]}
                    for row in cursor.fetchall()
                ]

            except Exception as e:
                self.results["errors"].append(f"Analysis failed: {str(e)}")
                analysis['error'] = str(e)

        self.results["checks"]["provision_analysis"] = analysis
        return analysis

    def check_existing_versions(self) -> Dict[str, any]:
        """Check if baseline versions already exist"""
        print("Checking existing document versions...")

        version_status = {}
        with self.conn.cursor() as cursor:
            try:
                # Count existing versions
                cursor.execute("SELECT COUNT(*) FROM versions.document_versions")
                version_status['total_versions'] = cursor.fetchone()[0]

                # Count baseline versions
                cursor.execute("""
                    SELECT COUNT(*) FROM versions.document_versions
                    WHERE version_number LIKE '%baseline%'
                """)
                version_status['baseline_versions'] = cursor.fetchone()[0]

                # Check version types
                cursor.execute("""
                    SELECT document_type, version_status, COUNT(*)
                    FROM versions.document_versions
                    GROUP BY document_type, version_status
                    ORDER BY document_type, version_status
                """)
                version_status['version_breakdown'] = [
                    {'type': row[0], 'status': row[1], 'count': row[2]}
                    for row in cursor.fetchall()
                ]

            except Exception as e:
                self.results["errors"].append(f"Version check failed: {str(e)}")
                version_status['error'] = str(e)

        self.results["checks"]["existing_versions"] = version_status
        return version_status

    def create_baseline_versions(self) -> bool:
        """Create baseline document versions if they don't exist"""
        print("Creating baseline document versions...")

        try:
            with self.conn.cursor() as cursor:
                # First, identify unique documents that need baseline versions
                cursor.execute("""
                    WITH document_analysis AS (
                        SELECT
                            CASE
                                WHEN document_id LIKE '%LEP%' THEN 'LEP'
                                WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
                                WHEN document_id LIKE '%DCP%' THEN 'DCP'
                                ELSE 'UNKNOWN'
                            END as document_type,
                            regexp_replace(document_id, '_.*', '') as document_identifier,
                            COUNT(*) as provision_count
                        FROM regulatory_provisions
                        WHERE document_id IS NOT NULL
                        GROUP BY document_type, document_identifier
                    )
                    SELECT
                        da.document_type,
                        da.document_identifier,
                        da.provision_count
                    FROM document_analysis da
                    LEFT JOIN versions.document_versions dv
                      ON da.document_identifier = dv.document_identifier
                      AND dv.version_number = 'v1.0-baseline'
                    WHERE dv.id IS NULL
                      AND da.document_type != 'UNKNOWN'
                    ORDER BY da.document_type, da.provision_count DESC
                """)

                documents_to_create = cursor.fetchall()

                if not documents_to_create:
                    print("All baseline versions already exist")
                    self.results["actions_taken"].append("No baseline versions needed - already exist")
                    return True

                print(f"Creating baseline versions for {len(documents_to_create)} documents")

                # Create baseline versions
                created_count = 0
                for doc_type, doc_identifier, provision_count in documents_to_create:
                    document_url = None
                    if doc_type == 'LEP':
                        document_url = 'https://legislation.nsw.gov.au/view/html/inforce/current/'
                    elif doc_type == 'SEPP':
                        document_url = 'https://legislation.nsw.gov.au/view/html/inforce/current/'

                    cursor.execute("""
                        INSERT INTO versions.document_versions (
                            document_type,
                            document_identifier,
                            version_number,
                            version_status,
                            effective_date,
                            document_url,
                            change_summary,
                            metadata,
                            created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        doc_type,
                        doc_identifier,
                        'v1.0-baseline',
                        'CURRENT',
                        self.baseline_date,
                        document_url,
                        'Baseline version from consolidated download Sept 2024',
                        json.dumps({
                            'baseline': True,
                            'consolidation_date': self.baseline_date,
                            'source': 'legislation.nsw.gov.au + council sites',
                            'provision_count': provision_count,
                            'coverage_note': 'Tracks changes from 2024-09-20 forward only',
                            'historical_coverage': 'none'
                        }),
                        'baseline_migration_script'
                    ))
                    created_count += 1

                self.conn.commit()
                self.results["actions_taken"].append(f"Created {created_count} baseline document versions")
                print(f"Created {created_count} baseline versions successfully")
                return True

        except Exception as e:
            self.results["errors"].append(f"Failed to create baseline versions: {str(e)}")
            print(f"Failed to create baseline versions: {e}")
            self.conn.rollback()
            return False

    def link_provisions_to_versions(self) -> bool:
        """Link existing provisions to their baseline document versions"""
        print("Linking provisions to baseline versions...")

        try:
            with self.conn.cursor() as cursor:
                # Count unlinked provisions
                cursor.execute("""
                    SELECT COUNT(*) FROM regulatory_provisions
                    WHERE version_id IS NULL AND document_id IS NOT NULL
                """)
                unlinked_count = cursor.fetchone()[0]

                if unlinked_count == 0:
                    print("All provisions already linked to versions")
                    self.results["actions_taken"].append("No provision linking needed - already linked")
                    return True

                print(f"Linking {unlinked_count} provisions to versions")

                # DEBUG: Check what we're trying to match
                cursor.execute("SELECT COUNT(*) FROM versions.document_versions WHERE version_number = 'v1.0-baseline'")
                baseline_versions = cursor.fetchone()[0]
                print(f"DEBUG: Found {baseline_versions} baseline document versions")

                cursor.execute("SELECT document_identifier FROM versions.document_versions WHERE version_number = 'v1.0-baseline' LIMIT 3")
                sample_identifiers = [row[0] for row in cursor.fetchall()]
                print(f"DEBUG: Sample document identifiers: {sample_identifiers}")

                cursor.execute("SELECT document_id FROM regulatory_provisions WHERE version_id IS NULL LIMIT 3")
                sample_doc_ids = [row[0] for row in cursor.fetchall()]
                print(f"DEBUG: Sample provision document_ids: {sample_doc_ids}")

                # Link provisions to baseline versions
                # First try exact match approach
                cursor.execute("""
                    UPDATE regulatory_provisions
                    SET
                        version_id = dv.id,
                        version_effective_date = dv.effective_date,
                        is_current = true
                    FROM versions.document_versions dv
                    WHERE (
                        regulatory_provisions.document_id LIKE dv.document_identifier || '%'
                        OR regexp_replace(regulatory_provisions.document_id, '_.*', '') = dv.document_identifier
                        OR regulatory_provisions.document_id = dv.document_identifier
                    )
                      AND dv.version_number = 'v1.0-baseline'
                      AND dv.version_status = 'CURRENT'
                      AND regulatory_provisions.version_id IS NULL
                """)

                linked_count = cursor.rowcount
                self.conn.commit()

                self.results["actions_taken"].append(f"Linked {linked_count} provisions to baseline versions")
                print(f"Linked {linked_count} provisions successfully")
                return True

        except Exception as e:
            self.results["errors"].append(f"Failed to link provisions: {str(e)}")
            print(f"Failed to link provisions: {e}")
            self.conn.rollback()
            return False

    def setup_change_tracking(self) -> bool:
        """Set up provision change tracking infrastructure"""
        print("Setting up change tracking infrastructure...")

        try:
            with self.conn.cursor() as cursor:
                # Check if table already exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'provision_changes'
                        AND table_schema = 'versions'
                    )
                """)
                table_exists = cursor.fetchone()[0]

                if table_exists:
                    print("Change tracking table already exists")
                    self.results["actions_taken"].append("Change tracking table already exists")
                else:
                    # Create provision changes table
                    cursor.execute("""
                        CREATE TABLE versions.provision_changes (
                            id SERIAL PRIMARY KEY,
                            document_version_id INTEGER REFERENCES versions.document_versions(id),
                            provision_id INTEGER REFERENCES regulatory_provisions(id),
                            change_type VARCHAR(20) CHECK (change_type IN ('NEW', 'MODIFIED', 'DELETED', 'UNCHANGED')),
                            old_content TEXT,
                            new_content TEXT,
                            change_summary TEXT,
                            change_metadata JSONB DEFAULT '{}',
                            effective_date DATE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_by VARCHAR(100) DEFAULT 'system'
                        )
                    """)

                    # Create indexes
                    cursor.execute("""
                        CREATE INDEX idx_provision_changes_provision
                        ON versions.provision_changes(provision_id)
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_provision_changes_document_version
                        ON versions.provision_changes(document_version_id)
                    """)
                    cursor.execute("""
                        CREATE INDEX idx_provision_changes_type_date
                        ON versions.provision_changes(change_type, effective_date)
                    """)

                    self.results["actions_taken"].append("Created provision_changes table and indexes")
                    print("Created change tracking table and indexes")

                # Check if baseline provisions already recorded
                cursor.execute("""
                    SELECT COUNT(*) FROM versions.provision_changes
                    WHERE created_by = 'baseline_migration_script'
                """)
                baseline_changes = cursor.fetchone()[0]

                if baseline_changes == 0:
                    # Record baseline provisions as initial state
                    cursor.execute("""
                        INSERT INTO versions.provision_changes (
                            document_version_id,
                            provision_id,
                            change_type,
                            new_content,
                            change_summary,
                            effective_date,
                            created_by
                        )
                        SELECT
                            rp.version_id,
                            rp.id,
                            'NEW' as change_type,
                            rp.provision_text,
                            'Baseline provision from consolidated download' as change_summary,
                            %s as effective_date,
                            'baseline_migration_script' as created_by
                        FROM regulatory_provisions rp
                        WHERE rp.version_id IS NOT NULL
                    """, (self.baseline_date,))

                    baseline_count = cursor.rowcount
                    self.results["actions_taken"].append(f"Recorded {baseline_count} baseline provision changes")
                    print(f"Recorded {baseline_count} baseline provision changes")
                else:
                    print("Baseline provision changes already recorded")
                    self.results["actions_taken"].append("Baseline provision changes already exist")

                self.conn.commit()
                return True

        except Exception as e:
            self.results["errors"].append(f"Failed to setup change tracking: {str(e)}")
            print(f"Failed to setup change tracking: {e}")
            self.conn.rollback()
            return False

    def verify_migration_integrity(self) -> Dict[str, any]:
        """Verify the integrity of the migration"""
        print("Verifying migration integrity...")

        integrity_checks = {}
        with self.conn.cursor() as cursor:
            try:
                # Check all provisions are versioned
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(version_id) as versioned,
                        COUNT(*) - COUNT(version_id) as unversioned
                    FROM regulatory_provisions
                """)
                result = cursor.fetchone()
                integrity_checks['provision_versioning'] = {
                    'total': result[0],
                    'versioned': result[1],
                    'unversioned': result[2],
                    'success': result[2] == 0
                }

                # Check document version coverage
                cursor.execute("""
                    SELECT
                        dv.document_type,
                        dv.document_identifier,
                        COUNT(rp.id) as linked_provisions
                    FROM versions.document_versions dv
                    LEFT JOIN regulatory_provisions rp ON dv.id = rp.version_id
                    WHERE dv.version_number = 'v1.0-baseline'
                    GROUP BY dv.document_type, dv.document_identifier
                    ORDER BY dv.document_type, linked_provisions DESC
                """)
                integrity_checks['document_coverage'] = [
                    {'type': row[0], 'identifier': row[1], 'provisions': row[2]}
                    for row in cursor.fetchall()
                ]

                # Check change tracking setup
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_changes,
                        COUNT(CASE WHEN change_type = 'NEW' THEN 1 END) as new_provisions,
                        COUNT(DISTINCT provision_id) as unique_provisions
                    FROM versions.provision_changes
                    WHERE created_by = 'baseline_migration_script'
                """)
                result = cursor.fetchone()
                integrity_checks['change_tracking'] = {
                    'total_changes': result[0],
                    'new_provisions': result[1],
                    'unique_provisions': result[2]
                }

                # Performance check
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM regulatory_provisions rp
                    JOIN versions.document_versions dv ON rp.version_id = dv.id
                    WHERE dv.version_status = 'CURRENT'
                """)
                current_provisions = cursor.fetchone()[0]
                integrity_checks['performance_ready'] = {
                    'current_provisions': current_provisions,
                    'query_optimized': current_provisions > 0
                }

            except Exception as e:
                self.results["errors"].append(f"Integrity verification failed: {str(e)}")
                integrity_checks['error'] = str(e)

        self.results["checks"]["migration_integrity"] = integrity_checks
        return integrity_checks

    def run_autocomplete_verification(self) -> bool:
        """Run complete autocomplete verification and implementation"""
        print("Starting PRP-V4-Enhanced Autocomplete Verification...")

        # Step 1: Analyze current state
        analysis = self.analyze_current_provisions()

        # Step 2: Check existing versions
        existing_versions = self.check_existing_versions()

        # Step 3: Create baseline versions if needed
        if not self.create_baseline_versions():
            return False

        # Step 4: Link provisions to versions
        if not self.link_provisions_to_versions():
            return False

        # Step 5: Setup change tracking
        if not self.setup_change_tracking():
            return False

        # Step 6: Verify migration integrity
        integrity = self.verify_migration_integrity()

        # Determine overall success
        success = (
            len(self.results["errors"]) == 0 and
            integrity.get('provision_versioning', {}).get('success', False) and
            integrity.get('change_tracking', {}).get('total_changes', 0) > 0
        )

        self.results["success"] = success
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "actions_taken": len(self.results["actions_taken"]),
            "provisions_versioned": integrity.get('provision_versioning', {}).get('versioned', 0),
            "documents_created": len(integrity.get('document_coverage', [])),
            "change_tracking_ready": integrity.get('change_tracking', {}).get('total_changes', 0) > 0
        }

        # Save results
        output_file = "verify_v4_enhanced_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("PRP-V4-ENHANCED AUTOCOMPLETE RESULTS")
        print("="*60)
        print(f"Provisions versioned: {integrity.get('provision_versioning', {}).get('versioned', 0)}")
        print(f"Documents with versions: {len(integrity.get('document_coverage', []))}")
        print(f"Change tracking records: {integrity.get('change_tracking', {}).get('total_changes', 0)}")
        print(f"Actions taken: {len(self.results['actions_taken'])}")

        if self.results["actions_taken"]:
            print("\nActions performed:")
            for action in self.results["actions_taken"]:
                print(f"  - {action}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  ERROR: {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  WARNING: {warning}")

        print(f"\n{'PRP-V4-ENHANCED AUTOCOMPLETE SUCCESS' if success else 'PRP-V4-ENHANCED AUTOCOMPLETE FAILED'}")
        print(f"Results saved to: {output_file}")

        return success

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

if __name__ == "__main__":
    verifier = PRPV4EnhancedVerification()
    try:
        success = verifier.run_autocomplete_verification()
        sys.exit(0 if success else 1)
    finally:
        verifier.close()
