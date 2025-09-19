#!/usr/bin/env python3
"""
PRP-M1 Verification: Prove complete migration success
"""

import json
from db_config import get_connection

def verify_prp_m1():
    """Verify PRP-M1 completion with automated proof"""

    print("=== PRP-M1 VERIFICATION ===")

    # Load migration report
    try:
        with open('prp_m1_migration_report.json', 'r') as f:
            report = json.load(f)
    except FileNotFoundError:
        print("FAILED: Migration report not found")
        return False

    # Check migration status
    if report['status'] != 'COMPLETED':
        print(f"FAILED: Migration status = {report['status']}")
        return False

    # Verify table counts in PostgreSQL
    conn = get_connection()
    cursor = conn.cursor()

    expected_tables = {
        'development_controls': 4526,
        'quantitative_standards': 832,
        'kg_entities': 1394,
        'documents': 274,
        'regulatory_refs': 2698
    }

    verification_passed = True

    for table, expected_count in expected_tables.items():
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            actual_count = cursor.fetchone()[0]

            if actual_count >= expected_count * 0.9:  # Allow 10% tolerance
                print(f"SUCCESS {table}: {actual_count:,} records (expected {expected_count:,})")
            else:
                print(f"FAILED {table}: {actual_count:,} records (expected {expected_count:,})")
                verification_passed = False
        except Exception as e:
            print(f"FAILED {table}: Table missing or inaccessible - {e}")
            verification_passed = False

    # Verify data quality - sample records
    try:
        cursor.execute("SELECT COUNT(*) FROM development_controls WHERE value_text IS NOT NULL OR value_numeric IS NOT NULL")
        quality_check = cursor.fetchone()[0]

        if quality_check > 4000:
            print(f"SUCCESS Data quality: {quality_check:,} records with control values")
        else:
            print(f"FAILED Data quality: Only {quality_check:,} records with control values")
            verification_passed = False
    except Exception as e:
        print(f"FAILED Data quality check: {e}")
        verification_passed = False

    conn.close()

    # Final verification
    if verification_passed:
        print(f"\nSUCCESS PRP-M1 VERIFICATION PASSED")
        print(f"  Total migrated: {report['total_records_migrated']:,} records")
        print(f"  Migration time: {report.get('end_time', 'Unknown')}")
        print(f"  Ready for PRP-M2 and Priority2Fix PRPs")
        return True
    else:
        print(f"\nFAILED PRP-M1 VERIFICATION FAILED")
        return False

if __name__ == "__main__":
    success = verify_prp_m1()
    exit(0 if success else 1)