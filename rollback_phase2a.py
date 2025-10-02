#!/usr/bin/env python3
"""
ROLLBACK Phase 2A Migration
============================
Restores ref_numbers and removes Phase 2A changes
"""

import sys
from db_config import get_connection

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
    """Remove all Phase 2A changes"""
    print_header("ROLLBACK PHASE 2A MIGRATION")

    print_warning("This will remove all Phase 2A changes:")
    print("  • Restore ref_numbers (add back arrows)")
    print("  • Revert duplicates marked in Phase 2A")
    print("  • Drop cross_reference_text column")
    print("  • Drop index")

    response = input("\n[WARNING] Are you sure? Type 'rollback' to confirm: ")
    if response != 'rollback':
        print("Rollback cancelled.")
        sys.exit(0)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Step 1: Restore ref_numbers from cross_reference_text
        print("\nRestoring ref_numbers...")
        cur.execute("""
            UPDATE regulatory_provisions
            SET ref_number = ref_number || ' -> ' || cross_reference_text
            WHERE cross_reference_text IS NOT NULL
              AND cross_reference_text != '';
        """)
        restored = cur.rowcount
        print_success(f"Restored {restored} ref_numbers")

        # Step 2: Revert is_canonical changes from Phase 2A
        print("Reverting duplicate markings...")
        cur.execute("""
            UPDATE regulatory_provisions
            SET
                is_canonical = TRUE,
                canonical_provision_id = NULL,
                migration_phase = 'phase1_canonical'
            WHERE migration_phase = 'phase2a_duplicate';
        """)
        reverted = cur.rowcount
        print_success(f"Reverted {reverted} provisions to canonical")

        # Step 3: Drop index
        print("Dropping index...")
        cur.execute("DROP INDEX IF EXISTS idx_provisions_cross_ref;")
        print_success("Index dropped")

        # Step 4: Drop column
        print("Dropping cross_reference_text column...")
        cur.execute("ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS cross_reference_text;")
        print_success("Column dropped")

        # Commit all changes
        conn.commit()
        print_success("\nRollback complete! Database restored to pre-Phase 2A state.")

    except Exception as e:
        print_error(f"Rollback failed: {e}")
        conn.rollback()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    rollback_migration()
