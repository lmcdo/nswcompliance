#!/usr/bin/env python3
"""
PRP-F4 Verification: Provision Linking Completion
Complete linking of remaining provisions to baseline document versions
"""

import os
import sys
import json
import psycopg2
from datetime import datetime
import re
from typing import Dict, List, Tuple, Any

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from db_config import get_connection

class ProvisionLinkingCompletion:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "F4",
            "objective": "Provision Linking Completion",
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

    def analyze_unlinked_provisions(self) -> Dict[str, Any]:
        """Analyze provisions that are not linked to versions"""
        print("Analyzing unlinked provisions...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Count total and unlinked provisions
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total_provisions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE version_id IS NULL")
            unlinked_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE version_id IS NOT NULL")
            linked_count = cursor.fetchone()[0]

            # Get sample of unlinked document IDs
            cursor.execute("""
                SELECT
                    document_id,
                    COUNT(*) as provision_count,
                    SUBSTRING(document_id, 1, 50) as doc_sample
                FROM regulatory_provisions
                WHERE version_id IS NULL
                GROUP BY document_id
                ORDER BY provision_count DESC
                LIMIT 20
            """)

            unlinked_samples = [
                {
                    "document_id": row[0],
                    "provision_count": row[1],
                    "sample": row[2]
                }
                for row in cursor.fetchall()
            ]

            conn.close()

            analysis = {
                "total_provisions": total_provisions,
                "linked_provisions": linked_count,
                "unlinked_provisions": unlinked_count,
                "link_percentage": (linked_count / total_provisions * 100) if total_provisions > 0 else 0,
                "unlinked_samples": unlinked_samples
            }

            print(f"  Total provisions: {total_provisions}")
            print(f"  Linked: {linked_count} ({analysis['link_percentage']:.1f}%)")
            print(f"  Unlinked: {unlinked_count}")

            self.results["actions_taken"].append("Analyzed unlinked provisions")
            return analysis

        except Exception as e:
            self.results["errors"].append(f"Unlinked provision analysis failed: {str(e)}")
            return {}

    def create_normalization_function(self) -> bool:
        """Create document identifier normalization function"""
        print("Creating document identifier normalization function...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                CREATE OR REPLACE FUNCTION normalize_document_identifier(doc_id TEXT)
                RETURNS TEXT AS $$
                DECLARE
                    normalized TEXT;
                BEGIN
                    -- Handle NULL input
                    IF doc_id IS NULL THEN
                        RETURN NULL;
                    END IF;

                    -- Start with the original document ID
                    normalized := doc_id;

                    -- Remove common suffixes and patterns
                    normalized := REGEXP_REPLACE(normalized, '_DCP.*$', '', 'i');
                    normalized := REGEXP_REPLACE(normalized, '_LEP.*$', '', 'i');
                    normalized := REGEXP_REPLACE(normalized, '_SEPP.*$', '', 'i');

                    -- Remove version numbers and dates
                    normalized := REGEXP_REPLACE(normalized, '_[0-9]{4}.*$', '');
                    normalized := REGEXP_REPLACE(normalized, '_v[0-9]+.*$', '', 'i');

                    -- Remove underscores and extra spaces
                    normalized := REGEXP_REPLACE(normalized, '_+', ' ', 'g');
                    normalized := REGEXP_REPLACE(normalized, '\\s+', ' ', 'g');

                    -- Remove special characters except alphanumeric and spaces
                    normalized := REGEXP_REPLACE(normalized, '[^A-Za-z0-9 ]', '', 'g');

                    -- Trim and convert to title case for consistency
                    normalized := TRIM(normalized);
                    normalized := INITCAP(normalized);

                    RETURN normalized;
                END;
                $$ LANGUAGE plpgsql;
            """)

            conn.commit()
            conn.close()

            print("  Normalization function created")
            self.results["actions_taken"].append("Created document identifier normalization function")
            return True

        except Exception as e:
            self.results["errors"].append(f"Failed to create normalization function: {str(e)}")
            return False

    def enable_similarity_extension(self) -> bool:
        """Enable PostgreSQL similarity extension for fuzzy matching"""
        print("Enabling similarity extension...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Check if extension exists
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
            extension_exists = cursor.fetchone() is not None

            if not extension_exists:
                # Try to create extension
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                    conn.commit()
                    print("  pg_trgm extension created")
                except Exception as e:
                    print(f"  Could not create pg_trgm extension: {str(e)}")
                    self.results["warnings"].append("pg_trgm extension not available - using basic matching")
                    conn.rollback()
                    conn.close()
                    return False
            else:
                print("  pg_trgm extension already available")

            # Test similarity function
            cursor.execute("SELECT similarity('test', 'test')")
            similarity_result = cursor.fetchone()[0]

            if similarity_result == 1.0:
                print("  Similarity function working correctly")
                conn.close()
                self.results["actions_taken"].append("Enabled similarity extension")
                return True
            else:
                print(f"  Similarity function returned unexpected result: {similarity_result}")
                conn.close()
                return False

        except Exception as e:
            self.results["errors"].append(f"Failed to enable similarity extension: {str(e)}")
            return False

    def find_document_matches(self, use_similarity: bool = True) -> List[Dict[str, Any]]:
        """Find potential document matches for unlinked provisions"""
        print("Finding document matches...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            if use_similarity:
                # Use similarity matching
                cursor.execute("""
                    WITH unlinked_docs AS (
                        SELECT DISTINCT
                            document_id,
                            normalize_document_identifier(document_id) as normalized_id,
                            COUNT(*) as provision_count
                        FROM regulatory_provisions
                        WHERE version_id IS NULL
                        GROUP BY document_id
                    ),
                    version_docs AS (
                        SELECT
                            id as version_id,
                            document_identifier,
                            document_type
                        FROM versions.document_versions
                    )
                    SELECT
                        ud.document_id,
                        ud.normalized_id,
                        ud.provision_count,
                        vd.version_id,
                        vd.document_identifier,
                        vd.document_type,
                        SIMILARITY(ud.normalized_id, vd.document_identifier) as similarity_score
                    FROM unlinked_docs ud
                    CROSS JOIN version_docs vd
                    WHERE SIMILARITY(ud.normalized_id, vd.document_identifier) > 0.5
                    ORDER BY ud.provision_count DESC, similarity_score DESC
                """)
            else:
                # Use basic string matching
                cursor.execute("""
                    WITH unlinked_docs AS (
                        SELECT DISTINCT
                            document_id,
                            normalize_document_identifier(document_id) as normalized_id,
                            COUNT(*) as provision_count
                        FROM regulatory_provisions
                        WHERE version_id IS NULL
                        GROUP BY document_id
                    ),
                    version_docs AS (
                        SELECT
                            id as version_id,
                            document_identifier,
                            document_type
                        FROM versions.document_versions
                    )
                    SELECT
                        ud.document_id,
                        ud.normalized_id,
                        ud.provision_count,
                        vd.version_id,
                        vd.document_identifier,
                        vd.document_type,
                        CASE
                            WHEN ud.normalized_id = vd.document_identifier THEN 1.0
                            WHEN ud.normalized_id ILIKE '%' || vd.document_identifier || '%' THEN 0.8
                            WHEN vd.document_identifier ILIKE '%' || ud.normalized_id || '%' THEN 0.7
                            ELSE 0.0
                        END as similarity_score
                    FROM unlinked_docs ud
                    CROSS JOIN version_docs vd
                    WHERE (
                        ud.normalized_id = vd.document_identifier OR
                        ud.normalized_id ILIKE '%' || vd.document_identifier || '%' OR
                        vd.document_identifier ILIKE '%' || ud.normalized_id || '%'
                    )
                    ORDER BY ud.provision_count DESC, similarity_score DESC
                """)

            matches = []
            for row in cursor.fetchall():
                match = {
                    "document_id": row[0],
                    "normalized_id": row[1],
                    "provision_count": row[2],
                    "version_id": row[3],
                    "document_identifier": row[4],
                    "document_type": row[5],
                    "similarity_score": float(row[6])
                }
                matches.append(match)

            conn.close()

            print(f"  Found {len(matches)} potential matches")
            self.results["actions_taken"].append(f"Found {len(matches)} document matches")
            return matches

        except Exception as e:
            self.results["errors"].append(f"Document matching failed: {str(e)}")
            return []

    def create_missing_versions(self, unmatched_docs: List[str]) -> int:
        """Create versions for documents that have no matches"""
        if not unmatched_docs:
            return 0

        print(f"Creating versions for {len(unmatched_docs)} unmatched documents...")
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            created_count = 0
            for doc_id in unmatched_docs:
                try:
                    # Determine document type from ID
                    if 'LEP' in doc_id.upper():
                        doc_type = 'LEP'
                    elif 'SEPP' in doc_id.upper():
                        doc_type = 'SEPP'
                    elif 'DCP' in doc_id.upper():
                        doc_type = 'DCP'
                    else:
                        doc_type = 'UNKNOWN'

                    # Create normalized identifier
                    normalized_id = self.normalize_document_id_python(doc_id)

                    cursor.execute("""
                        INSERT INTO versions.document_versions
                        (document_type, document_identifier, version_number, version_status,
                         effective_date, change_summary, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        doc_type,
                        normalized_id,
                        'v1.0-baseline',
                        'CURRENT',
                        '2024-09-01',  # Baseline date
                        'Auto-created baseline version for unmatched document',
                        '{}'
                    ))

                    version_id = cursor.fetchone()[0]
                    created_count += 1

                    print(f"  Created version {version_id} for {normalized_id}")

                except Exception as e:
                    print(f"  Failed to create version for {doc_id}: {str(e)}")
                    continue

            conn.commit()
            conn.close()

            print(f"  Created {created_count} new document versions")
            self.results["actions_taken"].append(f"Created {created_count} new document versions")
            return created_count

        except Exception as e:
            self.results["errors"].append(f"Version creation failed: {str(e)}")
            return 0

    def normalize_document_id_python(self, doc_id: str) -> str:
        """Python implementation of document ID normalization"""
        if not doc_id:
            return ""

        # Remove common suffixes
        normalized = re.sub(r'_DCP.*$', '', doc_id, flags=re.IGNORECASE)
        normalized = re.sub(r'_LEP.*$', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'_SEPP.*$', '', normalized, flags=re.IGNORECASE)

        # Remove version numbers and dates
        normalized = re.sub(r'_[0-9]{4}.*$', '', normalized)
        normalized = re.sub(r'_v[0-9]+.*$', '', normalized, flags=re.IGNORECASE)

        # Replace underscores with spaces
        normalized = re.sub(r'_+', ' ', normalized)
        normalized = re.sub(r'\\s+', ' ', normalized)

        # Remove special characters
        normalized = re.sub(r'[^A-Za-z0-9 ]', '', normalized)

        # Trim and title case
        normalized = normalized.strip().title()

        return normalized

    def link_provisions_to_versions(self, matches: List[Dict[str, Any]], similarity_threshold: float = 0.7) -> int:
        """Link provisions to versions based on matches"""
        print(f"Linking provisions to versions (threshold: {similarity_threshold})...")

        # Group matches by document_id, taking the best match for each
        best_matches = {}
        for match in matches:
            doc_id = match["document_id"]
            if (doc_id not in best_matches or
                match["similarity_score"] > best_matches[doc_id]["similarity_score"]):
                if match["similarity_score"] >= similarity_threshold:
                    best_matches[doc_id] = match

        print(f"  Found {len(best_matches)} documents with good matches")

        if not best_matches:
            return 0

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            linked_count = 0
            for doc_id, match in best_matches.items():
                try:
                    cursor.execute("""
                        UPDATE regulatory_provisions
                        SET version_id = %s
                        WHERE document_id = %s AND version_id IS NULL
                    """, (match["version_id"], doc_id))

                    updated_rows = cursor.rowcount
                    linked_count += updated_rows

                    print(f"  Linked {updated_rows} provisions from '{doc_id}' to version {match['version_id']} (similarity: {match['similarity_score']:.2f})")

                except Exception as e:
                    print(f"  Failed to link {doc_id}: {str(e)}")
                    continue

            conn.commit()
            conn.close()

            print(f"  Successfully linked {linked_count} provisions")
            self.results["actions_taken"].append(f"Linked {linked_count} provisions to versions")
            return linked_count

        except Exception as e:
            self.results["errors"].append(f"Provision linking failed: {str(e)}")
            return 0

    def verify_final_statistics(self) -> Dict[str, Any]:
        """Get final verification statistics"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Count provisions
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            total_provisions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE version_id IS NOT NULL")
            linked_provisions = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE version_id IS NULL")
            unlinked_provisions = cursor.fetchone()[0]

            # Count versions
            cursor.execute("SELECT COUNT(*) FROM versions.document_versions")
            total_versions = cursor.fetchone()[0]

            # Count distinct linked documents
            cursor.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions WHERE version_id IS NOT NULL")
            linked_documents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions WHERE version_id IS NULL")
            unlinked_documents = cursor.fetchone()[0]

            conn.close()

            link_percentage = (linked_provisions / total_provisions * 100) if total_provisions > 0 else 0

            stats = {
                "total_provisions": total_provisions,
                "linked_provisions": linked_provisions,
                "unlinked_provisions": unlinked_provisions,
                "link_percentage": link_percentage,
                "total_versions": total_versions,
                "linked_documents": linked_documents,
                "unlinked_documents": unlinked_documents,
                "success_criteria_met": link_percentage >= 95
            }

            return stats

        except Exception as e:
            self.results["errors"].append(f"Statistics collection failed: {str(e)}")
            return {}

    def execute_completion(self) -> bool:
        """Execute the complete provision linking completion"""
        print("Starting PRP-F4 Provision Linking Completion...")
        print("=" * 60)

        # Step 1: Analyze current state
        initial_analysis = self.analyze_unlinked_provisions()
        self.results["statistics"]["initial"] = initial_analysis

        if initial_analysis.get("unlinked_provisions", 0) == 0:
            print("All provisions already linked!")
            self.results["success"] = True
            return True

        # Step 2: Create normalization function
        if not self.create_normalization_function():
            return False

        # Step 3: Enable similarity extension
        similarity_available = self.enable_similarity_extension()

        # Step 4: Find document matches
        matches = self.find_document_matches(use_similarity=similarity_available)
        self.results["statistics"]["matches"] = {"count": len(matches), "matches": matches[:10]}  # Save first 10

        # Step 5: Link provisions
        linked_count = self.link_provisions_to_versions(matches)

        # Step 6: Handle unmatched documents
        if matches:
            matched_doc_ids = set(match["document_id"] for match in matches if match["similarity_score"] >= 0.7)
            unmatched_docs = [
                sample["document_id"]
                for sample in initial_analysis.get("unlinked_samples", [])
                if sample["document_id"] not in matched_doc_ids
            ]

            if unmatched_docs:
                created_versions = self.create_missing_versions(unmatched_docs[:10])  # Limit to 10 for safety
                if created_versions > 0:
                    # Re-run matching for newly created versions
                    new_matches = self.find_document_matches(use_similarity=similarity_available)
                    additional_linked = self.link_provisions_to_versions(new_matches)
                    linked_count += additional_linked

        # Step 7: Final verification
        final_stats = self.verify_final_statistics()
        self.results["statistics"]["final"] = final_stats

        # Determine success
        success = (
            len(self.results["errors"]) == 0 and
            final_stats.get("success_criteria_met", False)
        )

        self.results["success"] = success

        # Save results
        with open("verify_f4_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("PRP-F4 PROVISION LINKING COMPLETION RESULTS")
        print("=" * 60)
        print(f"Total provisions: {final_stats.get('total_provisions', 0)}")
        print(f"Linked provisions: {final_stats.get('linked_provisions', 0)}")
        print(f"Unlinked provisions: {final_stats.get('unlinked_provisions', 0)}")
        print(f"Link percentage: {final_stats.get('link_percentage', 0):.1f}%")
        print(f"Document versions: {final_stats.get('total_versions', 0)}")
        print(f"Actions taken: {len(self.results['actions_taken'])}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\nPRP-F4 PROVISION LINKING COMPLETION {'PASSED' if success else 'FAILED'}")

        return success

def main():
    """Main entry point"""
    completion = ProvisionLinkingCompletion()
    success = completion.execute_completion()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
