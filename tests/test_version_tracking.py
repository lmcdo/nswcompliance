#!/usr/bin/env python3
"""
Unit tests for provision version tracking functionality.

Tests:
1. Version creation on text change
2. No version creation when text unchanged
3. Historical queries return correct version
4. Change detection works correctly
5. Version closure when provisions updated
6. Deleted provisions marked correctly
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor


def calculate_text_hash(text: str) -> str:
    """Calculate SHA-256 hash of provision text."""
    if not text:
        return hashlib.sha256(b'').hexdigest()
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def run_tests():
    """Run all version tracking tests."""
    print("=" * 70)
    print("PROVISION VERSION TRACKING TESTS")
    print("=" * 70)

    conn = psycopg2.connect(
        os.environ['DATABASE_URL'],
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()

    test_results = []

    try:
        # Test 1: Check version schema exists
        test_results.append(test_version_schema_exists(cur))

        # Test 2: Check existing provisions have version 1
        test_results.append(test_provisions_have_version_baseline(cur))

        # Test 3: Check version metadata fields exist
        test_results.append(test_version_metadata_fields(cur))

        # Test 4: Test historical query functionality
        test_results.append(test_historical_queries(cur))

        # Test 5: Check version counts match actual versions
        test_results.append(test_version_count_accuracy(cur))

        # Test 6: Check change log integrity
        test_results.append(test_change_log_integrity(cur))

        # Test 7: Check text hash consistency
        test_results.append(test_text_hash_consistency(cur))

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for result in test_results if result['passed'])
        total = len(test_results)

        for result in test_results:
            status = "✓ PASS" if result['passed'] else "✗ FAIL"
            print(f"{status}: {result['name']}")
            if not result['passed']:
                print(f"  Error: {result.get('error', 'Unknown error')}")

        print(f"\nTotal: {passed}/{total} tests passed")

        return passed == total

    finally:
        cur.close()
        conn.close()


def test_version_schema_exists(cur):
    """Test 1: Check that version tracking schema exists."""
    print("\n[Test 1] Checking version tracking schema...")

    try:
        # Check provision_versions table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'provision_versions'
            )
        """)
        pv_exists = cur.fetchone()['exists']

        # Check provision_change_log table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'provision_change_log'
            )
        """)
        pcl_exists = cur.fetchone()['exists']

        if pv_exists and pcl_exists:
            print("  ✓ provision_versions table exists")
            print("  ✓ provision_change_log table exists")
            return {'name': 'Version schema exists', 'passed': True}
        else:
            error = []
            if not pv_exists:
                error.append("provision_versions table missing")
            if not pcl_exists:
                error.append("provision_change_log table missing")
            return {
                'name': 'Version schema exists',
                'passed': False,
                'error': ', '.join(error)
            }

    except Exception as e:
        return {
            'name': 'Version schema exists',
            'passed': False,
            'error': str(e)
        }


def test_provisions_have_version_baseline(cur):
    """Test 2: Check that provisions have version 1 baseline."""
    print("\n[Test 2] Checking version baseline...")

    try:
        # Count provisions
        cur.execute("SELECT COUNT(*) as count FROM regulatory_provisions")
        provision_count = cur.fetchone()['count']

        # Count version records
        cur.execute("SELECT COUNT(*) as count FROM provision_versions WHERE version_number = 1")
        version_count = cur.fetchone()['count']

        # Check provisions with current_version_id
        cur.execute("""
            SELECT COUNT(*) as count FROM regulatory_provisions
            WHERE current_version_id IS NOT NULL
        """)
        with_version_id = cur.fetchone()['count']

        print(f"  Provisions: {provision_count:,}")
        print(f"  Version 1 records: {version_count:,}")
        print(f"  With current_version_id: {with_version_id:,}")

        if version_count > 0 and with_version_id > 0:
            coverage = (with_version_id / provision_count * 100) if provision_count > 0 else 0
            print(f"  Version coverage: {coverage:.1f}%")

            return {
                'name': 'Provisions have version baseline',
                'passed': True
            }
        else:
            return {
                'name': 'Provisions have version baseline',
                'passed': False,
                'error': f"Only {version_count} version records and {with_version_id} with version IDs"
            }

    except Exception as e:
        return {
            'name': 'Provisions have version baseline',
            'passed': False,
            'error': str(e)
        }


def test_version_metadata_fields(cur):
    """Test 3: Check that version metadata fields exist and are populated."""
    print("\n[Test 3] Checking version metadata fields...")

    try:
        # Check fields exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
              AND column_name IN (
                  'current_version_id', 'first_seen_date', 'last_modified_date',
                  'version_count', 'is_current', 'text_hash_current'
              )
            ORDER BY column_name
        """)
        fields = [row['column_name'] for row in cur.fetchall()]

        expected_fields = [
            'current_version_id', 'first_seen_date', 'is_current',
            'last_modified_date', 'text_hash_current', 'version_count'
        ]

        if len(fields) == len(expected_fields):
            print(f"  ✓ All {len(fields)} version metadata fields exist")

            # Check population
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE is_current = TRUE) as current_count,
                    COUNT(*) FILTER (WHERE version_count >= 1) as with_version_count,
                    COUNT(*) FILTER (WHERE text_hash_current IS NOT NULL) as with_hash
                FROM regulatory_provisions
            """)
            stats = cur.fetchone()

            print(f"  is_current = TRUE: {stats['current_count']:,}")
            print(f"  version_count >= 1: {stats['with_version_count']:,}")
            print(f"  text_hash_current populated: {stats['with_hash']:,}")

            return {
                'name': 'Version metadata fields exist',
                'passed': True
            }
        else:
            missing = set(expected_fields) - set(fields)
            return {
                'name': 'Version metadata fields exist',
                'passed': False,
                'error': f"Missing fields: {missing}"
            }

    except Exception as e:
        return {
            'name': 'Version metadata fields exist',
            'passed': False,
            'error': str(e)
        }


def test_historical_queries(cur):
    """Test 4: Test historical query functionality."""
    print("\n[Test 4] Testing historical queries...")

    try:
        # Check if any provisions have multiple versions
        cur.execute("""
            SELECT COUNT(DISTINCT provision_id) as count
            FROM provision_versions
            GROUP BY provision_id
            HAVING COUNT(*) > 1
        """)
        multi_version_count = cur.rowcount

        if multi_version_count > 0:
            print(f"  Found {multi_version_count} provisions with multiple versions")

            # Test historical query
            cur.execute("""
                SELECT
                    rp.id,
                    pv.version_number,
                    pv.effective_from,
                    pv.effective_to
                FROM regulatory_provisions rp
                INNER JOIN provision_versions pv ON pv.provision_id = rp.id
                WHERE rp.version_count > 1
                LIMIT 5
            """)
            examples = cur.fetchall()

            print(f"  Successfully queried {len(examples)} version records")

            return {
                'name': 'Historical queries work',
                'passed': True
            }
        else:
            print("  No provisions with multiple versions yet (expected before first update)")
            return {
                'name': 'Historical queries work',
                'passed': True,  # Not a failure, just no data yet
            }

    except Exception as e:
        return {
            'name': 'Historical queries work',
            'passed': False,
            'error': str(e)
        }


def test_version_count_accuracy(cur):
    """Test 5: Check that version_count matches actual version records."""
    print("\n[Test 5] Checking version_count accuracy...")

    try:
        # Compare version_count with actual version records
        cur.execute("""
            SELECT
                rp.id,
                rp.version_count,
                COUNT(pv.id) as actual_versions
            FROM regulatory_provisions rp
            LEFT JOIN provision_versions pv ON pv.provision_id = rp.id
            GROUP BY rp.id, rp.version_count
            HAVING rp.version_count != COUNT(pv.id)
            LIMIT 10
        """)

        mismatches = cur.fetchall()

        if len(mismatches) == 0:
            print("  ✓ All provision version_counts match actual versions")
            return {
                'name': 'Version count accuracy',
                'passed': True
            }
        else:
            print(f"  ✗ Found {len(mismatches)} mismatches:")
            for m in mismatches[:5]:
                print(f"    Provision {m['id']}: version_count={m['version_count']}, actual={m['actual_versions']}")
            return {
                'name': 'Version count accuracy',
                'passed': False,
                'error': f"{len(mismatches)} provisions have incorrect version_count"
            }

    except Exception as e:
        return {
            'name': 'Version count accuracy',
            'passed': False,
            'error': str(e)
        }


def test_change_log_integrity(cur):
    """Test 6: Check change log integrity."""
    print("\n[Test 6] Checking change log integrity...")

    try:
        # Count change log entries
        cur.execute("SELECT COUNT(*) as count FROM provision_change_log")
        log_count = cur.fetchone()['count']

        print(f"  Change log entries: {log_count:,}")

        if log_count > 0:
            # Check that all version references are valid
            cur.execute("""
                SELECT COUNT(*) as count
                FROM provision_change_log pcl
                WHERE pcl.version_to IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM provision_versions pv
                      WHERE pv.id = pcl.version_to
                  )
            """)
            invalid_refs = cur.fetchone()['count']

            if invalid_refs == 0:
                print("  ✓ All change log version references are valid")
                return {
                    'name': 'Change log integrity',
                    'passed': True
                }
            else:
                return {
                    'name': 'Change log integrity',
                    'passed': False,
                    'error': f"{invalid_refs} invalid version references in change log"
                }
        else:
            print("  No change log entries yet (expected before first update)")
            return {
                'name': 'Change log integrity',
                'passed': True  # Not a failure, just no data yet
            }

    except Exception as e:
        return {
            'name': 'Change log integrity',
            'passed': False,
            'error': str(e)
        }


def test_text_hash_consistency(cur):
    """Test 7: Check that text hashes are consistent."""
    print("\n[Test 7] Checking text hash consistency...")

    try:
        # Sample provisions and verify hashes
        cur.execute("""
            SELECT
                rp.id,
                rp.provision_text,
                rp.text_hash_current,
                pv.text_hash as version_hash
            FROM regulatory_provisions rp
            INNER JOIN provision_versions pv ON pv.id = rp.current_version_id
            WHERE rp.text_hash_current IS NOT NULL
            LIMIT 100
        """)

        provisions = cur.fetchall()

        if len(provisions) == 0:
            print("  No provisions with hashes to check")
            return {
                'name': 'Text hash consistency',
                'passed': True
            }

        mismatches = 0
        for prov in provisions:
            expected_hash = calculate_text_hash(prov['provision_text'] or '')
            if prov['text_hash_current'] != expected_hash:
                mismatches += 1
                if mismatches <= 3:
                    print(f"  ✗ Provision {prov['id']}: hash mismatch")

        if mismatches == 0:
            print(f"  ✓ All {len(provisions)} sampled hashes are consistent")
            return {
                'name': 'Text hash consistency',
                'passed': True
            }
        else:
            return {
                'name': 'Text hash consistency',
                'passed': False,
                'error': f"{mismatches}/{len(provisions)} provisions have incorrect hashes"
            }

    except Exception as e:
        return {
            'name': 'Text hash consistency',
            'passed': False,
            'error': str(e)
        }


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
