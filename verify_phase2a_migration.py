#!/usr/bin/env python3
"""
VERIFICATION SCRIPT FOR PHASE 2A MIGRATION
==========================================
Tests cross-reference cleanup migration
"""

import sys
from db_config import get_connection

def print_header(msg):
    print(f"\n{'='*80}")
    print(msg)
    print('='*80)

def print_result(test_name, passed, expected, actual, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status} {test_name}")
    if details:
        print(f"       {details}")
    if not passed:
        print(f"       Expected: {expected}, Actual: {actual}")

def verify_pre_migration():
    """Verify state before Phase 2A migration"""
    print_header("PRE-MIGRATION VERIFICATION")

    conn = get_connection()
    cur = conn.cursor()

    all_passed = True

    # Test 1: Phase 1 is complete
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name IN ('is_canonical', 'canonical_provision_id', 'text_hash');
    """)
    phase1_cols = [row[0] for row in cur.fetchall()]
    passed = len(phase1_cols) == 3
    print_result(
        "Phase 1 completed (required columns exist)",
        passed,
        "3 columns",
        f"{len(phase1_cols)} columns",
        f"Found: {', '.join(phase1_cols)}" if phase1_cols else "Phase 1 not complete!"
    )
    all_passed = all_passed and passed

    # Test 2: Count provisions with arrows
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE ref_number LIKE '%->%';
    """)
    arrow_count = cur.fetchone()[0]
    passed = arrow_count > 0
    print_result(
        "Provisions with cross-reference arrows exist",
        passed,
        "> 0",
        arrow_count,
        f"Found {arrow_count:,} provisions with arrows to clean"
    )
    all_passed = all_passed and passed

    # Test 3: Cross-reference column doesn't exist yet
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name = 'cross_reference_text';
    """)
    has_col = cur.fetchone() is not None
    passed = not has_col
    print_result(
        "cross_reference_text column does not exist yet",
        passed,
        "False",
        has_col,
        "Clean state" if passed else "Column already exists!"
    )
    all_passed = all_passed and passed

    conn.close()

    return all_passed

def verify_post_migration():
    """Verify state after Phase 2A migration"""
    print_header("POST-MIGRATION VERIFICATION")

    conn = get_connection()
    cur = conn.cursor()

    all_passed = True

    # Test 1: New column created
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name = 'cross_reference_text';
    """)
    result = cur.fetchone()
    passed = result is not None
    print_result(
        "cross_reference_text column created",
        passed,
        "column exists",
        "column exists" if passed else "column missing"
    )
    all_passed = all_passed and passed

    # Test 2: Cross-references preserved
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE cross_reference_text IS NOT NULL) as with_refs,
            COUNT(*) FILTER (WHERE LENGTH(cross_reference_text) > 0) as non_empty
        FROM regulatory_provisions;
    """)
    row = cur.fetchone()
    passed = row[2] > 2000  # Should have ~2,645 cross-refs preserved
    print_result(
        "Cross-references preserved in new column",
        passed,
        "~2,645",
        f"{row[2]:,}",
        f"{row[2]:,} provisions have cross-reference text preserved"
    )
    all_passed = all_passed and passed

    # Test 3: No arrows remain in ref_number
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE ref_number LIKE '%->%';
    """)
    arrows_remaining = cur.fetchone()[0]
    passed = arrows_remaining == 0
    print_result(
        "All arrows removed from ref_number",
        passed,
        "0",
        arrows_remaining,
        "ref_numbers cleaned" if passed else f"{arrows_remaining} still have arrows!"
    )
    all_passed = all_passed and passed

    # Test 4: New duplicates marked
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE migration_phase = 'phase2a_duplicate';
    """)
    new_dups = cur.fetchone()[0]
    passed = new_dups < 50  # Should be ~27
    print_result(
        "New duplicates revealed and marked",
        passed,
        "< 50",
        new_dups,
        f"{new_dups} new duplicates marked" if passed else "Too many duplicates!"
    )
    all_passed = all_passed and passed

    # Test 5: Canonical count updated
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
            COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
            COUNT(*) as total
        FROM regulatory_provisions;
    """)
    row = cur.fetchone()
    canonical_pct = (row[0] / row[2] * 100) if row[2] > 0 else 0
    passed = 85 <= canonical_pct <= 92
    print_result(
        "Canonical percentage reasonable",
        passed,
        "85-92%",
        f"{canonical_pct:.1f}%",
        f"{row[0]:,} canonical, {row[1]:,} duplicates"
    )
    all_passed = all_passed and passed

    # Test 6: Index created
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'regulatory_provisions'
          AND indexname = 'idx_provisions_cross_ref';
    """)
    has_index = cur.fetchone() is not None
    passed = has_index
    print_result(
        "Cross-reference index created",
        passed,
        "True",
        has_index
    )
    all_passed = all_passed and passed

    # Test 7: Sample data check
    print("\n  Sample cleaned provisions:")
    cur.execute("""
        SELECT
            id,
            ref_number,
            LEFT(cross_reference_text, 50) as cross_ref
        FROM regulatory_provisions
        WHERE cross_reference_text IS NOT NULL
        ORDER BY id
        LIMIT 5;
    """)
    for row in cur.fetchall():
        print(f"    ID {row[0]:5d}: {row[1]:30s} -> {row[2]}...")

    # Test 8: No orphaned duplicates
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions dup
        LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
        WHERE dup.is_canonical = FALSE
          AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);
    """)
    orphaned = cur.fetchone()[0]
    passed = orphaned == 0
    print_result(
        "No orphaned duplicates",
        passed,
        "0",
        orphaned,
        "All duplicates properly linked" if passed else f"{orphaned} orphaned!"
    )
    all_passed = all_passed and passed

    conn.close()

    return all_passed

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_phase2a_migration.py [pre|post]")
        sys.exit(1)

    phase = sys.argv[1].lower()

    if phase == 'pre':
        passed = verify_pre_migration()
    elif phase == 'post':
        passed = verify_post_migration()
    else:
        print(f"Unknown phase: {phase}")
        print("Use 'pre' or 'post'")
        sys.exit(1)

    print_header("VERIFICATION SUMMARY")
    if passed:
        print("  [PASS] ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("  [FAIL] SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()
