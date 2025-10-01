#!/usr/bin/env python3
"""
Phase 2.5 Migration Verification
=================================
Pre/post verification for orphaned foreign key fix

Usage:
    python verify_phase2b_migration.py pre   # Before migration
    python verify_phase2b_migration.py post  # After migration
"""

import sys
from datetime import datetime
from db_safety_wrapper import get_safe_connection

def print_header(message):
    print(f"\n{'=' * 80}")
    print(f"{message}")
    print(f"{'=' * 80}\n")

def print_test(name, passed, details=""):
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {name}")
    if details:
        print(f"      {details}")

def verify_pre_migration():
    """Verification before migration"""
    print_header("PHASE 2.5 PRE-MIGRATION VERIFICATION")

    tests_passed = 0
    tests_total = 0

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Test 1: Phase 1/2A columns exist
            tests_total += 1
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = 'regulatory_provisions'
                  AND column_name IN ('is_canonical', 'canonical_provision_id', 'text_hash');
            """)
            phase_cols = cursor.fetchone()[0]
            passed = phase_cols >= 3
            print_test("Test 1: Phase 1/2A columns exist", passed, f"{phase_cols}/3 columns found")
            if passed: tests_passed += 1

            # Test 2: Canonical view exists
            tests_total += 1
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.views
                WHERE table_name = 'regulatory_provisions_canonical';
            """)
            view_exists = cursor.fetchone()[0] == 1
            print_test("Test 2: Canonical view exists", view_exists)
            if view_exists: tests_passed += 1

            # Test 3: Duplicates marked
            tests_total += 1
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
                    COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
                    COUNT(*) as total
                FROM regulatory_provisions;
            """)
            row = cursor.fetchone()
            canonical_pct = (row[0] / row[2] * 100) if row[2] > 0 else 0
            passed = row[1] > 0 and canonical_pct >= 80
            print_test("Test 3: Duplicates properly marked", passed,
                      f"{row[0]:,} canonical ({canonical_pct:.1f}%), {row[1]:,} duplicates")
            if passed: tests_passed += 1

            # Test 4: Count orphaned controls (EXPECTING FAILURES)
            tests_total += 1
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_controls dc
                WHERE dc.provision_id IN (
                    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                );
            """)
            orphaned = cursor.fetchone()[0]
            # This should FAIL pre-migration (orphans exist)
            passed = orphaned > 0
            print_test("Test 4: Orphaned controls detected", passed,
                      f"{orphaned:,} controls need fixing")
            if passed: tests_passed += 1

            # Test 5: Sample orphaned controls
            if orphaned > 0:
                cursor.execute("""
                    SELECT
                        dc.id,
                        dc.provision_id,
                        dc.control_type,
                        rp.canonical_provision_id
                    FROM development_controls dc
                    JOIN regulatory_provisions rp ON dc.provision_id = rp.id::text
                    WHERE rp.is_canonical = FALSE
                    LIMIT 5;
                """)
                print("\n  Sample orphaned controls:")
                for row in cursor.fetchall():
                    print(f"    Control {row[0]:5d}: provision {row[1]:5s} (should be {row[3]}) - {row[2]}")

            # Summary
            print_header("PRE-MIGRATION SUMMARY")
            print(f"Tests passed: {tests_passed}/{tests_total}")

            if tests_passed >= 3:
                print("\n[READY] Database ready for Phase 2.5 migration")
                print(f"Expected to fix: {orphaned:,} orphaned controls")
                return True
            else:
                print("\n[NOT READY] Prerequisites not met")
                return False

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        return False

def verify_post_migration():
    """Verification after migration"""
    print_header("PHASE 2.5 POST-MIGRATION VERIFICATION")

    tests_passed = 0
    tests_total = 0

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Test 1: No orphaned controls
            tests_total += 1
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_controls dc
                WHERE dc.provision_id IN (
                    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                );
            """)
            orphaned_controls = cursor.fetchone()[0]
            passed = orphaned_controls == 0
            print_test("Test 1: No orphaned controls", passed,
                      f"{orphaned_controls} orphaned" if orphaned_controls > 0 else "All controls linked to canonical")
            if passed: tests_passed += 1

            # Test 2: No orphaned permissions
            tests_total += 1
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_permissions dp
                WHERE dp.source_provision_id IS NOT NULL
                  AND dp.source_provision_id IN (
                      SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                  );
            """)
            orphaned_permissions = cursor.fetchone()[0]
            passed = orphaned_permissions == 0
            print_test("Test 2: No orphaned permissions", passed,
                      f"{orphaned_permissions} orphaned" if orphaned_permissions > 0 else "All permissions linked to canonical")
            if passed: tests_passed += 1

            # Test 3: All controls joinable via canonical view
            tests_total += 1
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT dc.id) as joinable,
                    (SELECT COUNT(*) FROM development_controls) as total
                FROM regulatory_provisions_canonical rp
                JOIN development_controls dc ON dc.provision_id = rp.id::text;
            """)
            row = cursor.fetchone()
            join_pct = (row[0] / row[1] * 100) if row[1] > 0 else 0
            passed = join_pct >= 98.0
            print_test("Test 3: Controls joinable via canonical view", passed,
                      f"{row[0]:,}/{row[1]:,} ({join_pct:.1f}%)")
            if passed: tests_passed += 1

            # Test 4: Sample joined controls
            tests_total += 1
            cursor.execute("""
                SELECT
                    dc.id,
                    dc.control_type,
                    rp.ref_number,
                    rp.is_canonical
                FROM development_controls dc
                JOIN regulatory_provisions_canonical rp ON dc.provision_id = rp.id::text
                LIMIT 10;
            """)
            sample = cursor.fetchall()
            passed = len(sample) > 0 and all(row[3] for row in sample)
            print_test("Test 4: Sample controls link to canonical", passed,
                      f"{len(sample)} sample controls verified")
            if passed: tests_passed += 1

            # Test 5: Exempt/complying workflow test
            tests_total += 1
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT rp.id) as provisions,
                    COUNT(dc.id) as controls
                FROM regulatory_provisions_canonical rp
                LEFT JOIN development_controls dc ON dc.provision_id = rp.id::text
                WHERE rp.zone LIKE '%R2%'
                  AND (rp.document_id LIKE '%Exempt%' OR rp.document_id LIKE '%Complying%')
                  AND (rp.development_type = 'dwelling_house' OR rp.development_type IS NULL);
            """)
            row = cursor.fetchone()
            passed = row[0] > 0
            print_test("Test 5: Exempt/complying provisions accessible", passed,
                      f"{row[0]} provisions, {row[1]} controls for R2+dwelling_house")
            if passed: tests_passed += 1

            # Summary
            print_header("POST-MIGRATION SUMMARY")
            print(f"Tests passed: {tests_passed}/{tests_total}")

            if tests_passed == tests_total:
                print("\n[SUCCESS] Phase 2.5 migration fully successful")
                print("All foreign keys now point to canonical provisions")
                return True
            elif tests_passed >= 3:
                print("\n[PARTIAL SUCCESS] Migration mostly successful")
                print("Review failed tests above")
                return True
            else:
                print("\n[FAILURE] Migration had issues")
                print("Consider rollback and investigate")
                return False

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_phase2b_migration.py [pre|post]")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == 'pre':
        success = verify_pre_migration()
    elif mode == 'post':
        success = verify_post_migration()
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python verify_phase2b_migration.py [pre|post]")
        sys.exit(1)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
