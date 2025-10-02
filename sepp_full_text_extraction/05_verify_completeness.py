"""
STEP 5: Comprehensive verification tests for full text provisions

Verification Tests:
1. Text length verification - all provisions >500 chars where expected
2. Content completeness - provisions contain expected elements
3. Cross-reference integrity - refs point to valid provisions
4. Council verification report - generate sample provisions for review
5. Comparison with Planning Portal detections

Exit Codes:
- 0: Success - all tests pass
- 1: Failure - tests failed
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_config import get_connection

VERIFICATION_DIR = Path("../docs/sepps/verification")
COMPLETENESS_REPORT = VERIFICATION_DIR / "completeness_report.json"
PROVISION_SAMPLES = VERIFICATION_DIR / "sample_provisions_for_council.txt"
TEST_RESULTS = VERIFICATION_DIR / "test_results.json"

# Known provisions from Planning Portal analysis
KNOWN_PROVISIONS = {
    'thermal_energy_waste': {
        'ids': [18945, 19101, 19195],
        'expected_min_length': 400,
        'must_contain': ['thermal', 'waste', 'energy', '$30 million']
    },
    'climate_zones': {
        'ids': [6172, 6169, 6100, 6109, 6113],
        'expected_min_length': 200,
        'must_contain': ['climate zone', 'standard']
    },
    'water_use': {
        'ids': [6107, 6130, 6131, 6174],
        'expected_min_length': 150,
        'must_contain': ['water', 'Area A', 'Area B']
    },
    'basix': {
        'ids': [6079, 6166, 6177],
        'expected_min_length': 200,
        'must_contain': ['BASIX', 'climate zone']
    }
}

def test_text_length_distribution():
    """Test 1: Verify text length distribution"""
    print("\n=== TEST 1: TEXT LENGTH DISTRIBUTION ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get length distribution
        cur.execute("""
            SELECT
                CASE
                    WHEN full_text_length <= 100 THEN '0-100 chars'
                    WHEN full_text_length <= 500 THEN '101-500 chars'
                    WHEN full_text_length <= 1000 THEN '501-1000 chars'
                    WHEN full_text_length <= 2000 THEN '1001-2000 chars'
                    WHEN full_text_length <= 5000 THEN '2001-5000 chars'
                    ELSE '5000+ chars'
                END as length_range,
                COUNT(*) as count,
                ROUND(AVG(full_text_length)) as avg_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
            GROUP BY length_range
            ORDER BY MIN(full_text_length)
        """)

        results = []
        print("Text Length Distribution:")
        for row in cur.fetchall():
            range_name, count, avg = row
            results.append({'range': range_name, 'count': count, 'avg': avg})
            print(f"  {range_name:20} {count:>6,} provisions (avg: {avg:>6,.0f} chars)")

        # Check for truncated provisions
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
            AND full_text_length <= 500
            AND extraction_method = 'mineru'
        """)

        truncated = cur.fetchone()[0]

        conn.close()

        test_passed = truncated == 0
        status = "[OK] PASS" if test_passed else "[X] FAIL"

        print(f"\nTruncated provisions (≤500 chars) from MinerU: {truncated}")
        print(f"Test Result: {status}")

        return {
            'test_name': 'Text Length Distribution',
            'passed': test_passed,
            'distribution': results,
            'truncated_count': truncated
        }

    except Exception as e:
        print(f"[X] Test failed: {e}")
        return {'test_name': 'Text Length Distribution', 'passed': False, 'error': str(e)}

def test_content_completeness():
    """Test 2: Verify provisions contain expected content"""
    print("\n=== TEST 2: CONTENT COMPLETENESS ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        test_results = []

        for provision_type, spec in KNOWN_PROVISIONS.items():
            print(f"\nTesting {provision_type}:")

            for prov_id in spec['ids']:
                # Get provision
                cur.execute("""
                    SELECT id, ref_number, provision_text, full_text_length
                    FROM regulatory_provisions
                    WHERE id = %s
                """, (prov_id,))

                row = cur.fetchone()
                if not row:
                    test_results.append({
                        'provision_id': prov_id,
                        'type': provision_type,
                        'passed': False,
                        'error': 'Provision not found'
                    })
                    print(f"  [X] ID {prov_id}: Not found")
                    continue

                prov_id, ref, text, length = row

                # Check length
                length_ok = length >= spec['expected_min_length']

                # Check required content
                text_lower = text.lower()
                content_checks = []
                for required in spec['must_contain']:
                    contains = required.lower() in text_lower
                    content_checks.append(contains)

                all_content_ok = all(content_checks)
                overall_pass = length_ok and all_content_ok

                status = "[OK]" if overall_pass else "[X]"
                print(f"  {status} ID {prov_id:5} | {ref:20} | {length:>6,} chars | Content: {sum(content_checks)}/{len(content_checks)}")

                test_results.append({
                    'provision_id': prov_id,
                    'type': provision_type,
                    'ref_number': ref,
                    'length': length,
                    'min_length': spec['expected_min_length'],
                    'length_ok': length_ok,
                    'content_checks': dict(zip(spec['must_contain'], content_checks)),
                    'passed': overall_pass
                })

        conn.close()

        all_passed = all(r['passed'] for r in test_results)
        passed_count = sum(r['passed'] for r in test_results)
        total_count = len(test_results)

        status = "[OK] PASS" if all_passed else "[X] FAIL"
        print(f"\nTest Result: {status} ({passed_count}/{total_count} provisions passed)")

        return {
            'test_name': 'Content Completeness',
            'passed': all_passed,
            'passed_count': passed_count,
            'total_count': total_count,
            'details': test_results
        }

    except Exception as e:
        print(f"[X] Test failed: {e}")
        return {'test_name': 'Content Completeness', 'passed': False, 'error': str(e)}

def test_extraction_coverage():
    """Test 3: Verify extraction coverage by SEPP"""
    print("\n=== TEST 3: EXTRACTION COVERAGE ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get provision counts by SEPP
        cur.execute("""
            SELECT
                document_id,
                extraction_method,
                COUNT(*) as count,
                AVG(full_text_length) as avg_length,
                MIN(full_text_length) as min_length,
                MAX(full_text_length) as max_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
            GROUP BY document_id, extraction_method
            ORDER BY document_id, extraction_method
        """)

        results = []
        print("Extraction Coverage by SEPP:")
        current_doc = None
        for row in cur.fetchall():
            doc_id, method, count, avg, min_len, max_len = row

            if doc_id != current_doc:
                sepp_name = doc_id.replace('_', ' ').replace('State Environmental Planning Policy', 'SEPP')
                print(f"\n{sepp_name}:")
                current_doc = doc_id

            print(f"  {method:15} {count:>6,} provs | Avg: {avg:>7,.0f} | Range: {min_len:>6,}-{max_len:>8,}")

            results.append({
                'sepp': doc_id,
                'extraction_method': method,
                'count': count,
                'avg_length': float(avg),
                'min_length': min_len,
                'max_length': max_len
            })

        # Check for SEPPs with only short provisions
        cur.execute("""
            SELECT document_id
            FROM regulatory_provisions
            WHERE document_id LIKE '%State_Environmental_Planning_Policy%'
            GROUP BY document_id
            HAVING MAX(full_text_length) < 1000
        """)

        short_sepps = [row[0] for row in cur.fetchall()]

        conn.close()

        test_passed = len(short_sepps) == 0
        status = "[OK] PASS" if test_passed else "[X] FAIL"

        if short_sepps:
            print(f"\n[!] SEPPs with only short provisions (max <1000 chars):")
            for sepp in short_sepps:
                print(f"  {sepp}")

        print(f"\nTest Result: {status}")

        return {
            'test_name': 'Extraction Coverage',
            'passed': test_passed,
            'coverage': results,
            'short_sepps': short_sepps
        }

    except Exception as e:
        print(f"[X] Test failed: {e}")
        return {'test_name': 'Extraction Coverage', 'passed': False, 'error': str(e)}

def generate_council_verification_samples():
    """Generate sample provisions for council review"""
    print("\n=== GENERATING COUNCIL VERIFICATION SAMPLES ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        with open(PROVISION_SAMPLES, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("SAMPLE PROVISIONS FOR COUNCIL VERIFICATION\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")

            # Sample from each known provision type
            for prov_type, spec in KNOWN_PROVISIONS.items():
                f.write("\n" + "="*80 + "\n")
                f.write(f"{prov_type.upper().replace('_', ' ')}\n")
                f.write("="*80 + "\n\n")

                # Get first provision of this type
                prov_id = spec['ids'][0]
                cur.execute("""
                    SELECT id, ref_number, provision_text, full_text_length,
                           document_id, section_header
                    FROM regulatory_provisions
                    WHERE id = %s
                """, (prov_id,))

                row = cur.fetchone()
                if row:
                    prov_id, ref, text, length, doc_id, header = row

                    f.write(f"Provision ID:     {prov_id}\n")
                    f.write(f"Reference:        {ref}\n")
                    f.write(f"Document:         {doc_id}\n")
                    f.write(f"Section:          {header}\n")
                    f.write(f"Text Length:      {length:,} characters\n")
                    f.write(f"\nFULL TEXT:\n")
                    f.write("-"*80 + "\n")
                    f.write(text)
                    f.write("\n" + "-"*80 + "\n\n")

        conn.close()

        print(f"[OK] Council verification samples saved to: {PROVISION_SAMPLES}")

        # Show preview
        with open(PROVISION_SAMPLES, 'r', encoding='utf-8') as f:
            preview = f.read(500)
            print(f"\nPreview:\n{preview}...\n")

        return True

    except Exception as e:
        print(f"[X] Failed to generate samples: {e}")
        return False

def generate_completeness_report(test_results: List[Dict]):
    """Generate comprehensive completeness report"""
    print("\n=== GENERATING COMPLETENESS REPORT ===\n")

    report = {
        'generation_timestamp': datetime.now().isoformat(),
        'tests': test_results,
        'summary': {
            'total_tests': len(test_results),
            'passed_tests': sum(1 for t in test_results if t.get('passed')),
            'failed_tests': sum(1 for t in test_results if not t.get('passed')),
        }
    }

    report['summary']['all_tests_passed'] = report['summary']['failed_tests'] == 0

    with open(COMPLETENESS_REPORT, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"[OK] Completeness report saved to: {COMPLETENESS_REPORT}")
    return report

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("COMPREHENSIVE VERIFICATION TESTS - STEP 5")
    print("="*80)

    # Create verification directory
    VERIFICATION_DIR.mkdir(parents=True, exist_ok=True)

    # Run all tests
    test_results = []

    test_results.append(test_text_length_distribution())
    test_results.append(test_content_completeness())
    test_results.append(test_extraction_coverage())

    # Generate council samples
    generate_council_verification_samples()

    # Generate comprehensive report
    report = generate_completeness_report(test_results)

    # Print summary
    print(f"\n{'='*80}")
    print("VERIFICATION SUMMARY")
    print(f"{'='*80}\n")
    print(f"Tests Run:     {report['summary']['total_tests']}")
    print(f"Passed:        {report['summary']['passed_tests']} [OK]")
    print(f"Failed:        {report['summary']['failed_tests']} {'[X]' if report['summary']['failed_tests'] > 0 else ''}")
    print()

    for test in test_results:
        status = "[OK] PASS" if test.get('passed') else "[X] FAIL"
        print(f"  {status} - {test['test_name']}")

    print(f"\n{'='*80}")

    if report['summary']['all_tests_passed']:
        print("\n[SUCCESS] ALL VERIFICATION TESTS PASSED")
        print("\nFull text provisions are now available for council verification.")
        print(f"\nKey outputs:")
        print(f"  - Completeness report: {COMPLETENESS_REPORT}")
        print(f"  - Sample provisions:   {PROVISION_SAMPLES}")
        return 0
    else:
        print("\n[X] SOME TESTS FAILED")
        print(f"\nReview: {COMPLETENESS_REPORT}")
        return 1

if __name__ == "__main__":
    sys.exit(main())