#!/usr/bin/env python3
"""
SEPP Deduplication Script

Removes duplicate SEPP extractions, keeping only the canonical (largest) version
of each SEPP type. Does NOT delete any SEPP types entirely.

Usage:
    python scripts/deduplicate_sepps.py --dry-run   # Preview changes
    python scripts/deduplicate_sepps.py             # Apply changes
"""
import os
import sys
import argparse
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2


def get_db_url() -> str:
    """Get database URL from environment."""
    return os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')


def categorize_sepp(document_id: str) -> str:
    """Categorize a document_id into a SEPP type."""
    doc_lower = document_id.lower()

    if 'housing' in doc_lower:
        return 'SEPP_Housing'
    elif 'exempt' in doc_lower or 'complying' in doc_lower:
        return 'SEPP_Exempt_Complying'
    elif 'transport' in doc_lower and 'infrastructure' in doc_lower:
        return 'SEPP_Transport_Infrastructure'
    elif 'biodiversity' in doc_lower or 'conservation' in doc_lower:
        return 'SEPP_Biodiversity_Conservation'
    elif 'industry' in doc_lower or 'employment' in doc_lower:
        return 'SEPP_Industry_Employment'
    elif 'resilience' in doc_lower or 'hazard' in doc_lower:
        return 'SEPP_Resilience_Hazards'
    elif 'primary' in doc_lower and 'production' in doc_lower:
        return 'SEPP_Primary_Production'
    elif 'sustainable' in doc_lower or 'building' in doc_lower:
        return 'SEPP_Sustainable_Buildings'
    elif 'planning' in doc_lower and 'system' in doc_lower:
        return 'SEPP_Planning_Systems'
    else:
        return 'SEPP_Other'


class SEPPDeduplicator:
    """Deduplicate SEPP extractions."""

    def __init__(self, dry_run: bool = False):
        self.conn = psycopg2.connect(get_db_url())
        self.dry_run = dry_run
        self.stats = {
            'total_before': 0,
            'total_after': 0,
            'docs_before': 0,
            'docs_after': 0,
            'deleted': 0,
        }

    def close(self):
        self.conn.close()

    def analyze(self):
        """Analyze current SEPP state and plan deduplication."""
        cur = self.conn.cursor()

        # Get all SEPP documents with their provision counts
        cur.execute("""
            SELECT document_id, COUNT(*) as provisions
            FROM regulatory_provisions
            WHERE document_id ILIKE '%sepp%'
               OR document_id ILIKE '%state_environmental%'
            GROUP BY document_id
            ORDER BY provisions DESC
        """)

        # Group by SEPP type
        sepp_groups = defaultdict(list)
        for doc_id, count in cur.fetchall():
            sepp_type = categorize_sepp(doc_id)
            sepp_groups[sepp_type].append((doc_id, count))
            self.stats['total_before'] += count
            self.stats['docs_before'] += 1

        # Determine what to keep and what to delete
        to_keep = {}
        to_delete = []

        for sepp_type, docs in sepp_groups.items():
            # Sort by provision count descending
            docs_sorted = sorted(docs, key=lambda x: -x[1])

            # Keep the one with most provisions
            canonical = docs_sorted[0]
            to_keep[sepp_type] = canonical

            # Mark others for deletion
            for doc_id, count in docs_sorted[1:]:
                to_delete.append((sepp_type, doc_id, count))

        cur.close()
        return sepp_groups, to_keep, to_delete

    def execute(self, to_delete: list):
        """Execute the deduplication (delete non-canonical versions)."""
        if not to_delete:
            print("Nothing to delete.")
            return

        cur = self.conn.cursor()

        for sepp_type, doc_id, count in to_delete:
            if self.dry_run:
                print(f"  [DRY RUN] Would delete: {doc_id} ({count} provisions)")
            else:
                # First delete cross-references pointing to these provisions
                cur.execute("""
                    DELETE FROM cross_reference_index
                    WHERE source_provision_id IN (
                        SELECT id FROM regulatory_provisions WHERE document_id = %s
                    )
                """, (doc_id,))

                # Delete sepp_structured_requirements FK references
                cur.execute("""
                    DELETE FROM sepp_structured_requirements
                    WHERE source_provision_id IN (
                        SELECT id FROM regulatory_provisions WHERE document_id = %s
                    )
                """, (doc_id,))

                # Then delete the provisions
                cur.execute("""
                    DELETE FROM regulatory_provisions
                    WHERE document_id = %s
                """, (doc_id,))

                self.stats['deleted'] += count
                print(f"  Deleted: {doc_id} ({count} provisions)")

        if not self.dry_run:
            self.conn.commit()

        cur.close()

    def print_report(self, sepp_groups: dict, to_keep: dict, to_delete: list):
        """Print deduplication report."""
        print("\n" + "=" * 80)
        print("SEPP DEDUPLICATION REPORT")
        print("=" * 80)

        print(f"\nMode: {'DRY RUN' if self.dry_run else 'APPLIED'}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        print("\n--- Current State ---")
        for sepp_type, docs in sorted(sepp_groups.items()):
            print(f"\n{sepp_type}: {len(docs)} document version(s)")
            for doc_id, count in docs[:3]:  # Show first 3
                marker = " [KEEP]" if to_keep.get(sepp_type, (None,))[0] == doc_id else ""
                print(f"    {count:>6} provisions: {doc_id[:60]}{marker}")
            if len(docs) > 3:
                print(f"    ... and {len(docs) - 3} more versions")

        print("\n--- Deduplication Plan ---")
        print(f"Documents before: {self.stats['docs_before']}")
        print(f"Documents to delete: {len(to_delete)}")
        print(f"Documents after: {self.stats['docs_before'] - len(to_delete)}")

        provisions_to_delete = sum(d[2] for d in to_delete)
        print(f"\nProvisions before: {self.stats['total_before']:,}")
        print(f"Provisions to delete: {provisions_to_delete:,}")
        print(f"Provisions after: {self.stats['total_before'] - provisions_to_delete:,}")

        print("\n--- Canonical Versions (will be kept) ---")
        for sepp_type, (doc_id, count) in sorted(to_keep.items()):
            print(f"  {sepp_type}: {count:,} provisions")

        if self.dry_run:
            print("\n[DRY RUN] No changes made. Run without --dry-run to apply.")


def main():
    parser = argparse.ArgumentParser(description='Deduplicate SEPP extractions')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    args = parser.parse_args()

    deduplicator = SEPPDeduplicator(dry_run=args.dry_run)

    try:
        print("Analyzing SEPP documents...")
        sepp_groups, to_keep, to_delete = deduplicator.analyze()

        deduplicator.print_report(sepp_groups, to_keep, to_delete)

        if to_delete:
            print("\n--- Executing Deduplication ---")
            deduplicator.execute(to_delete)
            print("\nDeduplication complete.")

    finally:
        deduplicator.close()


if __name__ == '__main__':
    main()
