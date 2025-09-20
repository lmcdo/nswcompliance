# PRP-V4: Data Migration Pipeline

## Objective
Migrate existing regulatory data to version-aware schema, establishing initial versions for all documents.

## Prerequisites
- PRP-V1, V2, V3 completed
- Database backup taken
- Maintenance window scheduled (est. 30 minutes)

## Migration Strategy

### Phase 1: Document Identification
Identify unique documents and assign initial versions

### Phase 2: Version Creation
Create CURRENT version records for all existing documents

### Phase 3: Provision Linking
Link existing provisions to their document versions

### Phase 4: Validation
Ensure data integrity and no data loss

## Implementation

### File: migrate_to_versions.py
```python
#!/usr/bin/env python3
"""
Migration script to add version support to existing data
Safe, resumable, and reversible
"""

import logging
import json
from datetime import date, datetime
from typing import Dict, List, Set
import psycopg2
from psycopg2.extras import RealDictCursor
from db_config import get_connection
from services.version_manager import DocumentType, VersionStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VersionMigration:
    """Handles migration of existing data to versioned schema"""

    def __init__(self, dry_run: bool = True):
        self.conn = get_connection()
        self.dry_run = dry_run
        self.migration_log = []
        self.checkpoint_file = "migration_checkpoint.json"

    def analyze_existing_documents(self) -> Dict:
        """Analyze existing documents to determine version requirements"""
        logger.info("Analyzing existing documents...")

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get unique documents from regulatory_provisions
            cursor.execute("""
                SELECT DISTINCT
                    document_id,
                    COUNT(*) as provision_count,
                    MIN(created_at) as earliest_date,
                    MAX(created_at) as latest_date
                FROM regulatory_provisions
                WHERE document_id IS NOT NULL
                GROUP BY document_id
                ORDER BY document_id
            """)

            documents = cursor.fetchall()

            # Classify documents by type
            classified = {
                'SEPP': [],
                'LEP': [],
                'DCP': [],
                'UNKNOWN': []
            }

            for doc in documents:
                doc_id = doc['document_id']
                if 'SEPP' in doc_id.upper():
                    doc_type = 'SEPP'
                elif 'LEP' in doc_id.upper():
                    doc_type = 'LEP'
                elif 'DCP' in doc_id.upper():
                    doc_type = 'DCP'
                else:
                    doc_type = 'UNKNOWN'

                classified[doc_type].append(doc)

            summary = {
                'total_documents': len(documents),
                'documents_by_type': {k: len(v) for k, v in classified.items()},
                'classified_documents': classified,
                'total_provisions': sum(d['provision_count'] for d in documents)
            }

            logger.info(f"Found {summary['total_documents']} unique documents")
            logger.info(f"Classification: {summary['documents_by_type']}")

            return summary

    def create_initial_versions(self) -> Dict:
        """Create initial version records for existing documents"""
        logger.info("Creating initial document versions...")

        analysis = self.analyze_existing_documents()
        created_versions = []

        with self.conn.cursor() as cursor:
            if not self.dry_run:
                cursor.execute("BEGIN")

            try:
                for doc_type in ['SEPP', 'LEP', 'DCP']:
                    documents = analysis['classified_documents'][doc_type]

                    for doc in documents:
                        doc_id = doc['document_id']

                        # Check if version already exists
                        cursor.execute("""
                            SELECT id FROM versions.document_versions
                            WHERE document_identifier = %s
                            AND version_status = 'CURRENT'
                        """, (doc_id,))

                        if cursor.fetchone():
                            logger.info(f"Version already exists for {doc_id}, skipping")
                            continue

                        # Determine effective date (use earliest provision date)
                        effective_date = doc['earliest_date'].date() if doc['earliest_date'] else date(2022, 1, 1)

                        # Create version record
                        insert_sql = """
                            INSERT INTO versions.document_versions
                            (document_type, document_identifier, version_number,
                             version_status, effective_date, metadata, created_by)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """

                        version_metadata = {
                            'migration': True,
                            'original_provision_count': doc['provision_count'],
                            'migration_date': datetime.now().isoformat()
                        }

                        if not self.dry_run:
                            cursor.execute(insert_sql, (
                                doc_type,
                                doc_id,
                                'v1.0',  # Initial version
                                VersionStatus.CURRENT.value,
                                effective_date,
                                json.dumps(version_metadata),
                                'migration_script'
                            ))

                            version_id = cursor.fetchone()[0]
                            created_versions.append({
                                'document_id': doc_id,
                                'version_id': version_id,
                                'document_type': doc_type
                            })
                        else:
                            logger.info(f"DRY RUN: Would create version for {doc_id}")

                if not self.dry_run:
                    cursor.execute("COMMIT")
                    logger.info(f"Created {len(created_versions)} version records")

                return {
                    'created_count': len(created_versions),
                    'versions': created_versions
                }

            except Exception as e:
                if not self.dry_run:
                    cursor.execute("ROLLBACK")
                logger.error(f"Failed to create versions: {e}")
                raise

    def link_provisions_to_versions(self) -> Dict:
        """Link existing provisions to their document versions"""
        logger.info("Linking provisions to versions...")

        with self.conn.cursor() as cursor:
            if not self.dry_run:
                cursor.execute("BEGIN")

            try:
                # Update provisions with version IDs
                update_sql = """
                    UPDATE regulatory_provisions rp
                    SET
                        version_id = dv.id,
                        is_current = true,
                        version_effective_date = dv.effective_date
                    FROM versions.document_versions dv
                    WHERE rp.document_id = dv.document_identifier
                      AND dv.version_status = 'CURRENT'
                      AND rp.version_id IS NULL
                """

                if not self.dry_run:
                    cursor.execute(update_sql)
                    updated_count = cursor.rowcount
                    cursor.execute("COMMIT")
                    logger.info(f"Updated {updated_count} provisions with version IDs")
                else:
                    # Count how many would be updated
                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM regulatory_provisions rp
                        JOIN versions.document_versions dv
                          ON rp.document_id = dv.document_identifier
                        WHERE dv.version_status = 'CURRENT'
                          AND rp.version_id IS NULL
                    """)
                    would_update = cursor.fetchone()[0]
                    logger.info(f"DRY RUN: Would update {would_update} provisions")
                    updated_count = would_update

                return {'updated_provisions': updated_count}

            except Exception as e:
                if not self.dry_run:
                    cursor.execute("ROLLBACK")
                logger.error(f"Failed to link provisions: {e}")
                raise

    def validate_migration(self) -> Dict:
        """Validate the migration was successful"""
        logger.info("Validating migration...")

        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            checks = {}

            # Check 1: All documents have versions
            cursor.execute("""
                SELECT COUNT(DISTINCT document_id) as unversioned_docs
                FROM regulatory_provisions
                WHERE version_id IS NULL
                  AND document_id IS NOT NULL
            """)
            checks['unversioned_documents'] = cursor.fetchone()['unversioned_docs']

            # Check 2: Version counts match
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT document_identifier) as version_count
                FROM versions.document_versions
                WHERE version_status = 'CURRENT'
            """)
            version_count = cursor.fetchone()['version_count']

            cursor.execute("""
                SELECT COUNT(DISTINCT document_id) as doc_count
                FROM regulatory_provisions
                WHERE document_id IS NOT NULL
            """)
            doc_count = cursor.fetchone()['doc_count']

            checks['version_count'] = version_count
            checks['document_count'] = doc_count
            checks['counts_match'] = version_count == doc_count

            # Check 3: All provisions linked
            cursor.execute("""
                SELECT
                    COUNT(*) as total_provisions,
                    COUNT(version_id) as versioned_provisions
                FROM regulatory_provisions
            """)
            prov_stats = cursor.fetchone()
            checks['provision_stats'] = prov_stats
            checks['all_provisions_versioned'] = (
                prov_stats['total_provisions'] == prov_stats['versioned_provisions']
            )

            # Overall validation
            checks['migration_valid'] = (
                checks['unversioned_documents'] == 0 and
                checks['counts_match'] and
                checks['all_provisions_versioned']
            )

            logger.info(f"Validation result: {checks['migration_valid']}")
            logger.info(f"Validation details: {json.dumps(checks, indent=2)}")

            return checks

    def rollback_migration(self):
        """Rollback the migration if needed"""
        logger.warning("Rolling back migration...")

        with self.conn.cursor() as cursor:
            cursor.execute("BEGIN")

            try:
                # Remove version links from provisions
                cursor.execute("""
                    UPDATE regulatory_provisions
                    SET version_id = NULL,
                        is_current = NULL,
                        version_effective_date = NULL
                    WHERE version_id IS NOT NULL
                """)

                # Delete created versions
                cursor.execute("""
                    DELETE FROM versions.document_versions
                    WHERE created_by = 'migration_script'
                """)

                cursor.execute("COMMIT")
                logger.info("Migration rolled back successfully")

            except Exception as e:
                cursor.execute("ROLLBACK")
                logger.error(f"Failed to rollback: {e}")
                raise

    def run_migration(self):
        """Execute the complete migration"""
        logger.info(f"Starting migration (dry_run={self.dry_run})")

        try:
            # Step 1: Analyze
            analysis = self.analyze_existing_documents()
            self.migration_log.append({
                'step': 'analysis',
                'result': analysis,
                'timestamp': datetime.now().isoformat()
            })

            # Step 2: Create versions
            versions = self.create_initial_versions()
            self.migration_log.append({
                'step': 'create_versions',
                'result': versions,
                'timestamp': datetime.now().isoformat()
            })

            # Step 3: Link provisions
            linking = self.link_provisions_to_versions()
            self.migration_log.append({
                'step': 'link_provisions',
                'result': linking,
                'timestamp': datetime.now().isoformat()
            })

            # Step 4: Validate
            validation = self.validate_migration()
            self.migration_log.append({
                'step': 'validation',
                'result': validation,
                'timestamp': datetime.now().isoformat()
            })

            # Save migration log
            with open(f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
                json.dump(self.migration_log, f, indent=2)

            if validation['migration_valid']:
                logger.info("Migration completed successfully!")
                return True
            else:
                logger.error("Migration validation failed")
                if not self.dry_run:
                    self.rollback_migration()
                return False

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            if not self.dry_run:
                self.rollback_migration()
            raise

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Migrate data to versioned schema')
    parser.add_argument('--execute', action='store_true',
                       help='Execute migration (default is dry run)')
    parser.add_argument('--rollback', action='store_true',
                       help='Rollback previous migration')

    args = parser.parse_args()

    migration = VersionMigration(dry_run=not args.execute)

    if args.rollback:
        migration.rollback_migration()
    else:
        migration.run_migration()
```

## Execution Steps

1. **Dry Run First**
```bash
python migrate_to_versions.py
```

2. **Review Dry Run Output**
- Check document counts
- Verify classification accuracy
- Review provisions that would be updated

3. **Execute Migration**
```bash
python migrate_to_versions.py --execute
```

4. **Validate Results**
- Check migration log file
- Verify all provisions linked
- Test API queries

5. **Rollback if Needed**
```bash
python migrate_to_versions.py --rollback
```

## Verification Checklist

### Pre-Migration
- [ ] Database backup completed
- [ ] Dry run successful
- [ ] Stakeholders notified
- [ ] Maintenance window confirmed

### Migration Execution
- [ ] All documents identified correctly
- [ ] Version records created
- [ ] Provisions linked to versions
- [ ] No data loss
- [ ] Validation passed

### Post-Migration
- [ ] API endpoints working
- [ ] Version queries return data
- [ ] Performance acceptable
- [ ] Migration log saved
- [ ] Rollback tested (in dev)

## Success Criteria

1. ✅ 100% of documents have version records
2. ✅ 100% of provisions linked to versions
3. ✅ No data loss or corruption
4. ✅ Migration completes in <30 minutes
5. ✅ Rollback capability verified

## Next Steps

1. Run `verify_v4_migration.py` to validate
2. Proceed to PRP-V5_FRONTEND_INTEGRATION.md
3. Monitor system for 24 hours post-migration