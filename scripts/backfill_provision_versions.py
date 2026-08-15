#!/usr/bin/env python3
"""
Backfill provision_versions table with Version 1 baseline.

This script:
1. Creates version 1 for all 47,818 provisions in regulatory_provisions
2. Calculates text hashes for change detection
3. Sets effective_from dates from last_updated/created_at
4. Updates regulatory_provisions with current_version_id references
5. Validates the backfill with comprehensive checks

Usage:
    python scripts/backfill_provision_versions.py [--dry-run] [--batch-size 1000]

Options:
    --dry-run       Run validation checks without making changes
    --batch-size N  Process N provisions at a time (default: 1000)
"""

import os
import sys
import argparse
import hashlib
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor


def calculate_text_hash(text: str) -> str:
    """Calculate SHA-256 hash of provision text."""
    if not text:
        return hashlib.sha256(b'').hexdigest()
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def fetch_all_provisions(cur) -> List[Dict[str, Any]]:
    """Fetch all provisions from regulatory_provisions."""
    print("\nFetching all provisions from regulatory_provisions...")

    cur.execute("""
        SELECT
            id,
            provision_text,
            provision_type,
            v2_topic,
            v2_applicable_zones,
            v2_applicable_dev_types,
            v2_has_numeric_value,
            document_id,
            last_updated,
            created_at
        FROM regulatory_provisions
        ORDER BY id
    """)

    provisions = cur.fetchall()
    print(f"[OK] Fetched {len(provisions)} provisions")
    return provisions


def create_version_1_records(provisions: List[Dict[str, Any]], batch_size: int = 1000) -> List[Dict[str, Any]]:
    """
    Create version 1 records for all provisions.
    Returns list of (provision_id, version_id, text_hash) tuples.
    """
    version_records = []

    print(f"\nPreparing {len(provisions)} version 1 records...")

    for prov in provisions:
        # Calculate text hash
        text_hash = calculate_text_hash(prov['provision_text'] or '')

        # Determine effective_from date
        # Priority: last_updated > created_at > fallback to 2024-01-01
        effective_from = prov.get('last_updated') or prov.get('created_at')
        if not effective_from:
            effective_from = datetime(2024, 1, 1)

        version_records.append({
            'provision_id': prov['id'],
            'version_number': 1,
            'provision_text': prov['provision_text'],
            'provision_type': prov.get('provision_type'),
            'v2_topic': prov.get('v2_topic'),
            'v2_applicable_zones': prov.get('v2_applicable_zones'),
            'v2_applicable_dev_types': prov.get('v2_applicable_dev_types'),
            'v2_has_numeric_value': prov.get('v2_has_numeric_value'),
            'effective_from': effective_from,
            'effective_to': None,  # NULL = current
            'change_type': 'created',
            'text_hash': text_hash,
            'extracted_from_document': prov.get('document_id'),
            'extraction_method': 'backfill_script'
        })

    print(f"[OK] Prepared {len(version_records)} version records")
    return version_records


def insert_version_records(conn, cur, version_records: List[Dict[str, Any]], batch_size: int = 1000):
    """Insert version records in batches."""
    print(f"\nInserting version records (batch size: {batch_size})...")

    insert_query = """
        INSERT INTO provision_versions (
            provision_id, version_number, provision_text, provision_type,
            v2_topic, v2_applicable_zones, v2_applicable_dev_types,
            v2_has_numeric_value, effective_from, effective_to,
            change_type, text_hash, extracted_from_document, extraction_method
        ) VALUES (
            %(provision_id)s, %(version_number)s, %(provision_text)s, %(provision_type)s,
            %(v2_topic)s, %(v2_applicable_zones)s, %(v2_applicable_dev_types)s,
            %(v2_has_numeric_value)s, %(effective_from)s, %(effective_to)s,
            %(change_type)s, %(text_hash)s, %(extracted_from_document)s, %(extraction_method)s
        )
        RETURNING id, provision_id, text_hash
    """

    # Process in batches
    total = len(version_records)
    provision_version_map = {}  # provision_id -> (version_id, text_hash)

    for i in range(0, total, batch_size):
        batch = version_records[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} records)...")

        # Insert batch and collect returned IDs
        for record in batch:
            cur.execute(insert_query, record)
            result = cur.fetchone()
            if result:
                version_id, provision_id, text_hash = result
                provision_version_map[provision_id] = (version_id, text_hash)

        # Commit after each batch
        conn.commit()

    print(f"[OK] Inserted {len(provision_version_map)} version records")
    return provision_version_map


def update_provisions_with_version_refs(conn, cur, provision_version_map: Dict[int, tuple], batch_size: int = 1000):
    """Update regulatory_provisions with version references."""
    print(f"\nUpdating regulatory_provisions with version references...")

    update_query = """
        UPDATE regulatory_provisions
        SET
            current_version_id = %(version_id)s,
            first_seen_date = (
                SELECT effective_from FROM provision_versions WHERE id = %(version_id)s
            ),
            last_modified_date = NOW(),
            version_count = 1,
            is_current = TRUE,
            text_hash_current = %(text_hash)s
        WHERE id = %(provision_id)s
    """

    # Prepare update records
    update_records = [
        {
            'provision_id': prov_id,
            'version_id': version_id,
            'text_hash': text_hash
        }
        for prov_id, (version_id, text_hash) in provision_version_map.items()
    ]

    # Execute in batches
    total = len(update_records)
    for i in range(0, total, batch_size):
        batch = update_records[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} records)...")
        execute_batch(cur, update_query, batch, page_size=batch_size)
        conn.commit()

    print(f"[OK] Updated {len(update_records)} provisions")


def validate_backfill(cur):
    """Run validation queries to ensure backfill succeeded."""
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    checks_passed = 0
    checks_total = 0

    # Check 1: All provisions have current_version_id
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions WHERE current_version_id IS NULL
    """)
    null_count = cur.fetchone()[0]
    if null_count == 0:
        print("\n[OK] Check 1 PASSED: All provisions have current_version_id")
        checks_passed += 1
    else:
        print(f"\n[FAIL] Check 1 FAILED: {null_count} provisions have NULL current_version_id")

    # Check 2: All provisions have text_hash_current
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions WHERE text_hash_current IS NULL
    """)
    null_hash_count = cur.fetchone()[0]
    if null_hash_count == 0:
        print("[OK] Check 2 PASSED: All provisions have text_hash_current")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 2 FAILED: {null_hash_count} provisions have NULL text_hash_current")

    # Check 3: All provisions have is_current = TRUE
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions WHERE is_current = FALSE
    """)
    not_current_count = cur.fetchone()[0]
    if not_current_count == 0:
        print("[OK] Check 3 PASSED: All provisions have is_current = TRUE")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 3 FAILED: {not_current_count} provisions have is_current = FALSE")

    # Check 4: All provisions have version_count = 1
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions WHERE version_count != 1
    """)
    wrong_version_count = cur.fetchone()[0]
    if wrong_version_count == 0:
        print("[OK] Check 4 PASSED: All provisions have version_count = 1")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 4 FAILED: {wrong_version_count} provisions have version_count != 1")

    # Check 5: provision_versions has correct count
    checks_total += 1
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
    provision_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM provision_versions WHERE version_number = 1")
    version_count = cur.fetchone()[0]

    if provision_count == version_count:
        print(f"[OK] Check 5 PASSED: provision_versions has {version_count} version 1 records")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 5 FAILED: Expected {provision_count} version records, got {version_count}")

    # Check 6: All version records have effective_to = NULL (current)
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM provision_versions
        WHERE version_number = 1 AND effective_to IS NOT NULL
    """)
    closed_version_count = cur.fetchone()[0]
    if closed_version_count == 0:
        print("[OK] Check 6 PASSED: All version 1 records have effective_to = NULL")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 6 FAILED: {closed_version_count} version 1 records have non-NULL effective_to")

    # Check 7: All version records have non-empty text_hash
    checks_total += 1
    cur.execute("""
        SELECT COUNT(*) FROM provision_versions
        WHERE text_hash IS NULL OR text_hash = ''
    """)
    empty_hash_count = cur.fetchone()[0]
    if empty_hash_count == 0:
        print("[OK] Check 7 PASSED: All version records have text_hash")
        checks_passed += 1
    else:
        print(f"[FAIL] Check 7 FAILED: {empty_hash_count} version records have empty text_hash")

    # Summary
    print("\n" + "=" * 70)
    print(f"VALIDATION SUMMARY: {checks_passed}/{checks_total} checks passed")
    print("=" * 70)

    return checks_passed == checks_total


def run_backfill(dry_run: bool = False, batch_size: int = 1000):
    """Main backfill logic."""
    print("=" * 70)
    print("PROVISION VERSIONS BACKFILL")
    print("=" * 70)

    if dry_run:
        print("\n[WARN] DRY RUN MODE - No changes will be made\n")

    # Connect to database
    conn = psycopg2.connect(
        os.environ['DATABASE_URL'],
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()

    # Set statement timeout to 10 minutes for long-running operations
    cur.execute("SET statement_timeout = '600s'")
    print("Set statement_timeout to 600 seconds (10 minutes)")

    try:
        # Step 1: Fetch all provisions
        provisions = fetch_all_provisions(cur)

        if not provisions:
            print("\n[FAIL] No provisions found in database")
            return False

        # Step 2: Create version 1 records
        version_records = create_version_1_records(provisions, batch_size)

        if dry_run:
            print("\n[WARN] DRY RUN - Skipping database modifications")
            print(f"\nWould create {len(version_records)} version records")
            return True

        # Step 3: Insert version records
        provision_version_map = insert_version_records(conn, cur, version_records, batch_size)

        # Step 4: Update provisions with version references
        update_provisions_with_version_refs(conn, cur, provision_version_map, batch_size)

        # Step 5: Validate
        validation_passed = validate_backfill(cur)

        if validation_passed:
            print("\n[OK] All validation checks passed")
            print("[OK] Backfill completed successfully!")
            return True
        else:
            print("\n[FAIL] Validation failed - rolling back changes")
            conn.rollback()
            return False

    except Exception as e:
        print(f"\n[FAIL] Error during backfill: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Backfill provision_versions table with version 1 baseline'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run validation checks without making changes'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of records to process per batch (default: 1000)'
    )

    args = parser.parse_args()

    success = run_backfill(dry_run=args.dry_run, batch_size=args.batch_size)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
