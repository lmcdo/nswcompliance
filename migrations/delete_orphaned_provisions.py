#!/usr/bin/env python3
"""
Delete Orphaned Provisions - Data Quality Cleanup
=================================================
Deletes 815 provisions with document_ids that don't match any documents table entry.

Analysis:
- 695 provisions (85%): Image references with empty text
- 120 provisions (15%): Legacy metadata (doc_0, doc_105, etc.)
- 0 provisions with regulatory content

Impact:
- Total provisions: 22,648 → 21,833 (-815, -3.6%)
- Referential integrity: 96.4% → 100%
- No loss of regulatory content

Safety:
- Dry run mode first
- Transaction rollback on errors
- Detailed logging of deletions
- Backup recommendation
"""

import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection
from datetime import datetime


class OrphanedProvisionDeleter:
    def __init__(self, dry_run=True):
        self.conn = get_safe_connection()
        self.cursor = self.conn.cursor()
        self.dry_run = dry_run
        self.deleted_count = 0
        self.error_count = 0
        self.deletions = []

    def analyze_orphaned_provisions(self):
        """Analyze what will be deleted"""
        print("\n" + "="*80)
        print("ANALYZING ORPHANED PROVISIONS")
        print("="*80)

        # Count total orphaned
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL;
        """)
        total_orphaned = self.cursor.fetchone()[0]
        print(f"\nTotal orphaned provisions: {total_orphaned:,}")

        # Breakdown by type
        self.cursor.execute("""
            WITH orphaned AS (
                SELECT rp.id, rp.ref_number, rp.provision_text, rp.document_id
                FROM regulatory_provisions rp
                LEFT JOIN documents d ON rp.document_id = d.id
                WHERE d.id IS NULL
            )
            SELECT
                CASE
                    WHEN ref_number LIKE 'img_%' THEN 'Image'
                    WHEN ref_number LIKE 'doc_%' THEN 'Legacy Metadata'
                    WHEN provision_text LIKE 'Images:%Tables:%Sections:%' THEN 'Document Summary'
                    ELSE 'Other'
                END as provision_type,
                COUNT(*) as count
            FROM orphaned
            GROUP BY provision_type
            ORDER BY count DESC;
        """)

        print("\nBreakdown by type:")
        for prov_type, count in self.cursor.fetchall():
            print(f"  {prov_type}: {count:,}")

        # Top orphaned documents
        self.cursor.execute("""
            SELECT rp.document_id, COUNT(*) as provision_count
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL
            GROUP BY rp.document_id
            ORDER BY COUNT(*) DESC
            LIMIT 10;
        """)

        print("\nTop 10 orphaned documents:")
        for doc_id, count in self.cursor.fetchall():
            doc_display = doc_id if doc_id != 'unknown' else '(unknown)'
            print(f"  {count:3d} provisions: {doc_display}")

        # Sample provisions to be deleted
        self.cursor.execute("""
            SELECT rp.id, rp.ref_number, rp.document_id,
                   LEFT(rp.provision_text, 60) as text_preview
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL
            ORDER BY rp.id
            LIMIT 5;
        """)

        print("\nSample provisions to be deleted:")
        for prov_id, ref_num, doc_id, text in self.cursor.fetchall():
            print(f"  ID {prov_id}: {ref_num}")
            print(f"    Document: {doc_id}")
            print(f"    Text: {text}...")
            print()

        return total_orphaned

    def get_orphaned_provisions(self):
        """Get list of all orphaned provision IDs"""
        self.cursor.execute("""
            SELECT rp.id, rp.ref_number, rp.document_id, rp.provision_text
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL
            ORDER BY rp.id;
        """)

        return self.cursor.fetchall()

    def delete_provisions(self, provisions):
        """Delete orphaned provisions"""
        print("\n" + "="*80)
        print(f"{'DRY RUN - ' if self.dry_run else ''}DELETING ORPHANED PROVISIONS")
        print("="*80)

        for prov_id, ref_num, doc_id, prov_text in provisions:
            deletion_record = {
                'provision_id': prov_id,
                'ref_number': ref_num,
                'document_id': doc_id,
                'text_preview': prov_text[:100] if prov_text else ''
            }

            if not self.dry_run:
                try:
                    self.cursor.execute("""
                        DELETE FROM regulatory_provisions
                        WHERE id = %s;
                    """, (prov_id,))

                    self.deleted_count += 1
                    self.deletions.append(deletion_record)

                except Exception as e:
                    print(f"  [ERROR] Failed to delete provision {prov_id}: {e}")
                    self.error_count += 1
                    self.conn.rollback()
                    raise
            else:
                self.deleted_count += 1
                self.deletions.append(deletion_record)

        if self.deleted_count % 100 == 0:
            print(f"  Processed {self.deleted_count} provisions...")

    def verify_deletion(self):
        """Verify that all orphaned provisions are gone"""
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)

        # Count remaining orphaned
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL;
        """)

        remaining_orphaned = self.cursor.fetchone()[0]

        # Count total provisions
        self.cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
        total_provisions = self.cursor.fetchone()[0]

        print(f"Provisions deleted: {self.deleted_count:,}")
        print(f"Errors: {self.error_count:,}")
        print(f"Remaining orphaned: {remaining_orphaned:,}")
        print(f"Total provisions remaining: {total_provisions:,}")

        if remaining_orphaned > 0:
            print(f"\n[WARNING] {remaining_orphaned} provisions still orphaned")
            return False
        else:
            print("\n[SUCCESS] All orphaned provisions deleted!")
            print("[SUCCESS] 100% referential integrity achieved!")
            return True

    def generate_report(self):
        """Generate detailed report of deletions"""
        print("\n" + "="*80)
        print("DELETION REPORT")
        print("="*80)

        if not self.deletions:
            print("No deletions made")
            return

        print(f"\nTotal deletions: {len(self.deletions):,}")
        print("\nSample deletions (first 10):")

        for i, deletion in enumerate(self.deletions[:10]):
            print(f"\n{i+1}. Provision {deletion['provision_id']}")
            print(f"   Ref: {deletion['ref_number']}")
            print(f"   Document: {deletion['document_id']}")
            if deletion['text_preview']:
                print(f"   Text: {deletion['text_preview']}...")

        if len(self.deletions) > 10:
            print(f"\n... and {len(self.deletions) - 10} more")

        # Save full report
        if not self.dry_run:
            report_file = f"migration_markers/delete_orphaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            Path("migration_markers").mkdir(exist_ok=True)

            with open(report_file, 'w') as f:
                json.dump({
                    'date': datetime.now().isoformat(),
                    'total_deleted': len(self.deletions),
                    'deletions': self.deletions
                }, f, indent=2)

            print(f"\n[OK] Full report saved to: {report_file}")

    def run(self):
        """Main execution flow"""
        print("="*80)
        print("DELETE ORPHANED PROVISIONS - DATA QUALITY CLEANUP")
        print("="*80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE DELETION'}")
        print(f"Started: {datetime.now().isoformat()}\n")

        # Step 1: Analyze
        total_orphaned = self.analyze_orphaned_provisions()

        if total_orphaned == 0:
            print("\n[SUCCESS] No orphaned provisions found!")
            return True

        # Step 2: Get provisions to delete
        provisions = self.get_orphaned_provisions()
        print(f"\nFound {len(provisions):,} provisions to delete")

        # Step 3: Delete
        self.delete_provisions(provisions)

        # Step 4: Commit or rollback
        if not self.dry_run:
            if self.error_count > 0:
                print("\n[WARNING] Errors occurred - rolling back all changes")
                self.conn.rollback()
                return False
            else:
                print(f"\n[OK] Committing {self.deleted_count} deletions...")
                self.conn.commit()

        # Step 5: Verify
        success = self.verify_deletion()

        # Step 6: Report
        self.generate_report()

        print("\n" + "="*80)
        if self.dry_run:
            print("DRY RUN COMPLETE")
            print("="*80)
            print("\nNo changes were made to the database.")
            print("Run with --live flag to delete provisions.")
        else:
            print("DELETION COMPLETE")
            print("="*80)
            print(f"Deleted: {self.deleted_count:,} provisions")
            print(f"Errors: {self.error_count:,}")

        return success

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Delete orphaned provisions')
    parser.add_argument('--live', action='store_true',
                       help='Apply deletions (default is dry run)')
    parser.add_argument('--no-backup-check', action='store_true',
                       help='Skip backup verification (NOT recommended)')

    args = parser.parse_args()

    # Safety check
    if args.live and not args.no_backup_check:
        print("\n" + "="*80)
        print("WARNING: SAFETY CHECK")
        print("="*80)
        print("\nThis migration will DELETE 815 provisions.")
        print("Have you created a database backup?")
        print("\nRecommended backup command:")
        print("  python create_backup.py")
        print("\nOr use PostgreSQL dump:")
        print('  pg_dump -U postgres nsw_planning > backup_before_orphan_deletion.sql')

        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("\nDeletion cancelled. Create a backup first!")
            return False

    # Run migration
    dry_run = not args.live
    deleter = OrphanedProvisionDeleter(dry_run=dry_run)

    try:
        success = deleter.run()
        return success
    finally:
        deleter.close()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
