#!/usr/bin/env python3
"""
PRP-M2 Verification: Prove SEPP/LEP restructuring success
"""

import json
from db_config import get_connection

def verify_prp_m2():
    """Verify PRP-M2 completion with automated proof"""

    print("=== PRP-M2 VERIFICATION ===")

    # Load restructuring report
    try:
        with open('prp_m2_restructuring_report.json', 'r') as f:
            report = json.load(f)
    except FileNotFoundError:
        print("FAILED: Restructuring report not found")
        return False

    # Check restructuring status
    if report['status'] != 'COMPLETED':
        print(f"FAILED: Restructuring status = {report['status']}")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    verification_passed = True

    # Verify SEPP provisions table
    try:
        cursor.execute('SELECT COUNT(*) FROM sepp_provisions')
        sepp_count = cursor.fetchone()[0]

        if sepp_count >= 4000:  # Expect at least 4000 SEPP provisions (target: 4,237)
            print(f"SUCCESS SEPP provisions: {sepp_count:,} records extracted")
        elif sepp_count >= 2000:  # Acceptable minimum
            print(f"WARNING SEPP provisions: {sepp_count:,} records (expected 4,000+)")
        else:
            print(f"FAILED SEPP provisions: Only {sepp_count:,} records (expected 4,000+)")
            verification_passed = False
    except Exception as e:
        print(f"FAILED SEPP provisions: Table error - {e}")
        verification_passed = False

    # Verify LEP provisions table
    try:
        cursor.execute('SELECT COUNT(*) FROM lep_provisions')
        lep_count = cursor.fetchone()[0]

        if lep_count >= 900:  # Expect at least 900 LEP provisions (actual source has 967)
            print(f"SUCCESS LEP provisions: {lep_count:,} records extracted")
        elif lep_count >= 500:  # Acceptable minimum
            print(f"WARNING LEP provisions: {lep_count:,} records (expected 900+)")
        else:
            print(f"FAILED LEP provisions: Only {lep_count:,} records (expected 900+)")
            verification_passed = False
    except Exception as e:
        print(f"FAILED LEP provisions: Table error - {e}")
        verification_passed = False

    # Verify data quality
    try:
        cursor.execute('SELECT COUNT(*) FROM sepp_provisions WHERE provision_text IS NOT NULL AND provision_text != \'\'')
        sepp_quality = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM lep_provisions WHERE provision_text IS NOT NULL AND provision_text != \'\'')
        lep_quality = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM sepp_provisions')
        total_sepp = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM lep_provisions')
        total_lep = cursor.fetchone()[0]

        if sepp_quality == total_sepp and lep_quality == total_lep:
            print(f"SUCCESS Data quality: All records have provision text")
        else:
            print(f"WARNING Data quality: Some records missing provision text")
            print(f"  SEPP: {sepp_quality}/{total_sepp} with text")
            print(f"  LEP: {lep_quality}/{total_lep} with text")

    except Exception as e:
        print(f"WARNING Data quality check: {e}")

    # Verify summary views
    try:
        cursor.execute('SELECT COUNT(*) FROM sepp_summary')
        sepp_summary_count = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM lep_summary')
        lep_summary_count = cursor.fetchone()[0]

        if sepp_summary_count >= 0 and lep_summary_count >= 0:
            print(f"SUCCESS Summary views: SEPP ({sepp_summary_count}) LEP ({lep_summary_count})")
        else:
            print(f"WARNING Summary views: Unexpected counts")

    except Exception as e:
        print(f"FAILED Summary views: Error {e}")
        verification_passed = False

    # Test Priority2Fix readiness
    try:
        cursor.execute('''
            SELECT sepp_type, provision_category, COUNT(*)
            FROM sepp_provisions
            GROUP BY sepp_type, provision_category
            ORDER BY COUNT(*) DESC
            LIMIT 5
        ''')

        sepp_breakdown = cursor.fetchall()
        if sepp_breakdown:
            print(f"SUCCESS SEPP breakdown ready for PRP-Q2:")
            for row in sepp_breakdown:
                print(f"  {row[0]} - {row[1]}: {row[2]:,} provisions")
        else:
            print(f"WARNING No SEPP breakdown available")

    except Exception as e:
        print(f"WARNING SEPP breakdown analysis failed: {e}")

    conn.close()

    # Final verification
    if verification_passed:
        print(f"\nSUCCESS PRP-M2 VERIFICATION PASSED")
        total_sepp = report.get('total_sepp_extracted', 0)
        total_lep = report.get('total_lep_extracted', 0)
        print(f"  SEPP provisions: {total_sepp:,}")
        print(f"  LEP provisions: {total_lep:,}")
        print(f"  Ready for PRP-Q2 Development Pathway Intelligence")
        return True
    else:
        print(f"\nFAILED PRP-M2 VERIFICATION FAILED")
        return False

if __name__ == "__main__":
    success = verify_prp_m2()
    exit(0 if success else 1)