#!/usr/bin/env python3
"""
ROLLBACK Phase 1 Migration
===========================
Removes Phase 1 changes and restores database to pre-migration state

This script:
1. Drops the canonical view
2. Removes foreign key constraint
3. Drops indexes
4. Removes added columns
"""

import sys
from db_config import get_connection

class Color:
    """Disabled for Windows console compatibility"""
    HEADER = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''

def print_header(message):
    print(f"\n{'=' * 80}")
    print(f"{message}")
    print(f"{'=' * 80}\n")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_warning(message):
    print(f"[WARNING] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def rollback_migration():
    """Remove all Phase 1 changes"""
    print_header("ROLLBACK PHASE 1 MIGRATION")

    print_warning("This will remove all Phase 1 changes:")
    print("  • Drop view: regulatory_provisions_canonical")
    print("  • Drop constraint: fk_canonical_provision")
    print("  • Drop indexes: idx_provisions_text_hash, idx_provisions_canonical, idx_provisions_canonical_id")
    print("  • Remove columns: is_canonical, canonical_provision_id, text_hash, migration_phase")

    response = input(f"\n[WARNING] Are you sure? Type 'rollback' to confirm: ")
    if response != 'rollback':
        print("Rollback cancelled.")
        sys.exit(0)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Step 1: Drop view
        print("\nDropping view...")
        cur.execute("DROP VIEW IF EXISTS regulatory_provisions_canonical;")
        print_success("View dropped")

        # Step 2: Drop foreign key constraint
        print("Dropping foreign key constraint...")
        cur.execute("ALTER TABLE regulatory_provisions DROP CONSTRAINT IF EXISTS fk_canonical_provision;")
        print_success("Constraint dropped")

        # Step 3: Drop indexes
        print("Dropping indexes...")
        cur.execute("DROP INDEX IF EXISTS idx_provisions_text_hash;")
        cur.execute("DROP INDEX IF EXISTS idx_provisions_canonical;")
        cur.execute("DROP INDEX IF EXISTS idx_provisions_canonical_id;")
        print_success("Indexes dropped")

        # Step 4: Drop columns
        print("Dropping columns...")
        cur.execute("ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS is_canonical;")
        cur.execute("ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS canonical_provision_id;")
        cur.execute("ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS text_hash;")
        cur.execute("ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS migration_phase;")
        print_success("Columns dropped")

        # Commit all changes
        conn.commit()
        print_success("\nRollback complete! Database restored to pre-migration state.")

    except Exception as e:
        print_error(f"Rollback failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    rollback_migration()
