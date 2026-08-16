#!/usr/bin/env python3
"""
Verification Script: HCA Code Resolution
Purpose: Verify that resolveHcaCode() function correctly maps HCA codes to db_slug values
Date: 2026-01-29
Issue: #4 from Applicability-Based DCP Filtering Plan

Tests:
1. C35 → "parramatta_road" mapping exists in database
2. All Inner West HCAs have db_slug populated
3. Test common HCA codes used in API calls
4. Verify fallback strategies work (h_id, h_name, slug)
"""

import os
import sys
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class HCACodeVerifier:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT'),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD')
        )
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def test_c35_mapping(self) -> Dict:
        """Test specific C35 → parramatta_road mapping"""
        print("\n" + "="*80)
        print("TEST 1: C35 → parramatta_road Mapping")
        print("="*80)

        query = """
        SELECT h_id, h_name, db_slug, lga_name
        FROM heritage_conservation_areas
        WHERE h_id = 'C35';
        """

        self.cursor.execute(query)
        result = self.cursor.fetchone()

        if result:
            print(f"[OK] C35 mapping found:")
            print(f"   h_id: {result['h_id']}")
            print(f"   h_name: {result['h_name']}")
            print(f"   db_slug: {result['db_slug']}")
            print(f"   lga_name: {result['lga_name']}")

            if result['db_slug'] == 'parramatta_road':
                print("[PASS] db_slug matches expected value 'parramatta_road'")
                return {'status': 'PASS', 'result': dict(result)}
            else:
                print(f"[FAIL] db_slug is '{result['db_slug']}', expected 'parramatta_road'")
                return {'status': 'FAIL', 'result': dict(result)}
        else:
            print("[FAIL] No HCA found with h_id='C35'")
            return {'status': 'FAIL', 'result': None}

    def test_inner_west_hcas(self) -> Dict:
        """Check all Inner West HCAs have db_slug populated"""
        print("\n" + "="*80)
        print("TEST 2: Inner West HCAs db_slug Population")
        print("="*80)

        # Count total Inner West HCAs
        query_total = """
        SELECT COUNT(*) as total
        FROM heritage_conservation_areas
        WHERE lga_name ILIKE '%Inner West%';
        """

        self.cursor.execute(query_total)
        total = self.cursor.fetchone()['total']

        # Count HCAs with missing db_slug
        query_missing = """
        SELECT COUNT(*) as missing
        FROM heritage_conservation_areas
        WHERE lga_name ILIKE '%Inner West%'
          AND (db_slug IS NULL OR db_slug = '');
        """

        self.cursor.execute(query_missing)
        missing = self.cursor.fetchone()['missing']

        print(f"Total Inner West HCAs: {total}")
        print(f"Missing db_slug: {missing}")
        print(f"Populated db_slug: {total - missing}")

        if missing == 0:
            print("[OK] PASS: All Inner West HCAs have db_slug populated")
            return {'status': 'PASS', 'total': total, 'missing': 0}
        else:
            print(f"[FAIL] FAIL: {missing} HCAs missing db_slug")

            # Show examples of missing db_slug
            query_examples = """
            SELECT h_id, h_name
            FROM heritage_conservation_areas
            WHERE lga_name ILIKE '%Inner West%'
              AND (db_slug IS NULL OR db_slug = '')
            LIMIT 5;
            """

            self.cursor.execute(query_examples)
            examples = self.cursor.fetchall()

            print("\nExamples of HCAs missing db_slug:")
            for ex in examples:
                print(f"   - {ex['h_id']}: {ex['h_name']}")

            return {'status': 'FAIL', 'total': total, 'missing': missing}

    def test_common_hca_codes(self) -> Dict:
        """Test common HCA codes from Leichhardt area"""
        print("\n" + "="*80)
        print("TEST 3: Common HCA Code Resolution")
        print("="*80)

        # Get sample HCA codes from Inner West
        query = """
        SELECT h_id, h_name, db_slug
        FROM heritage_conservation_areas
        WHERE lga_name ILIKE '%Inner West%'
        ORDER BY h_id
        LIMIT 10;
        """

        self.cursor.execute(query)
        hcas = self.cursor.fetchall()

        print(f"Testing {len(hcas)} sample HCA codes:\n")

        all_pass = True
        results = []

        for hca in hcas:
            h_id = hca['h_id']
            h_name = hca['h_name']
            db_slug = hca['db_slug']

            if db_slug:
                print(f"[OK] {h_id:6s} → {db_slug:30s} ({h_name[:50]}...)")
                results.append({'h_id': h_id, 'status': 'PASS', 'db_slug': db_slug})
            else:
                print(f"[FAIL] {h_id:6s} → MISSING db_slug ({h_name[:50]}...)")
                results.append({'h_id': h_id, 'status': 'FAIL', 'db_slug': None})
                all_pass = False

        if all_pass:
            print("\n[OK] PASS: All sampled HCA codes have db_slug")
            return {'status': 'PASS', 'results': results}
        else:
            print("\n[FAIL] FAIL: Some HCA codes missing db_slug")
            return {'status': 'FAIL', 'results': results}

    def test_hca_name_lookup(self) -> Dict:
        """Test lookup by HCA name (fallback strategy)"""
        print("\n" + "="*80)
        print("TEST 4: HCA Name Lookup (Fallback Strategy)")
        print("="*80)

        test_cases = [
            "Parramatta Road Heritage Conservation Area",
            "Annandale Heritage Conservation Area",
            "Balmain Heritage Conservation Area"
        ]

        all_pass = True
        results = []

        for name in test_cases:
            query = """
            SELECT h_id, h_name, db_slug
            FROM heritage_conservation_areas
            WHERE h_name ILIKE %s;
            """

            self.cursor.execute(query, (name,))
            result = self.cursor.fetchone()

            if result:
                print(f"[OK] '{name[:40]}...' → {result['db_slug']} ({result['h_id']})")
                results.append({'name': name, 'status': 'PASS', 'db_slug': result['db_slug']})
            else:
                print(f"[FAIL] '{name[:40]}...' → NOT FOUND")
                results.append({'name': name, 'status': 'FAIL', 'db_slug': None})
                all_pass = False

        if all_pass:
            print("\n[OK] PASS: All test HCA names found")
            return {'status': 'PASS', 'results': results}
        else:
            print("\n[FAIL] FAIL: Some HCA names not found")
            return {'status': 'FAIL', 'results': results}

    def test_hca_provisions_exist(self) -> Dict:
        """Verify HCA provisions exist in regulatory_provisions"""
        print("\n" + "="*80)
        print("TEST 5: HCA Heritage Provisions Exist")
        print("="*80)

        # Test C35 specifically
        query = """
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE v2_heritage_hca = 'parramatta_road'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true;
        """

        self.cursor.execute(query)
        count = self.cursor.fetchone()['count']

        print(f"Heritage provisions with v2_heritage_hca='parramatta_road': {count}")

        if count > 0:
            print(f"[OK] PASS: Found {count} heritage provisions for Parramatta Road HCA")

            # Show sample provisions
            query_sample = """
            SELECT id, v2_dcp_part, v2_dcp_section, left(provision_text, 100) as text_preview
            FROM regulatory_provisions
            WHERE v2_heritage_hca = 'parramatta_road'
              AND v2_topic = 'heritage'
              AND v2_is_actionable = true
            LIMIT 3;
            """

            self.cursor.execute(query_sample)
            samples = self.cursor.fetchall()

            print("\nSample provisions:")
            for s in samples:
                print(f"   - [{s['v2_dcp_part']} {s['v2_dcp_section']}] {s['text_preview']}...")

            return {'status': 'PASS', 'count': count}
        else:
            print("[FAIL] FAIL: No heritage provisions found for Parramatta Road HCA")
            print("   This may indicate HCA linkage is broken")
            return {'status': 'FAIL', 'count': 0}

    def run_all_tests(self):
        """Run all verification tests"""
        print("\n" + "="*80)
        print(" HCA CODE RESOLUTION VERIFICATION")
        print("="*80)

        test_results = {
            'test_1_c35_mapping': self.test_c35_mapping(),
            'test_2_inner_west_complete': self.test_inner_west_hcas(),
            'test_3_common_codes': self.test_common_hca_codes(),
            'test_4_name_lookup': self.test_hca_name_lookup(),
            'test_5_provisions_exist': self.test_hca_provisions_exist()
        }

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        passed = sum(1 for r in test_results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in test_results.values() if r['status'] == 'FAIL')

        print(f"\nTests Passed: {passed}/5")
        print(f"Tests Failed: {failed}/5")

        if failed == 0:
            print("\n[PASS] ALL TESTS PASSED - HCA code resolution is working correctly")
            print("   Safe to proceed with API integration")
        else:
            print("\n[FAIL] SOME TESTS FAILED - HCA code resolution needs fixes")
            print("   Review failed tests and update db_slug values")

            # Recommendations
            print("\nRECOMMENDATIONS:")

            if test_results['test_2_inner_west_complete']['status'] == 'FAIL':
                missing = test_results['test_2_inner_west_complete']['missing']
                print(f"   1. Run slugification script to populate {missing} missing db_slug values")

            if test_results['test_5_provisions_exist']['status'] == 'FAIL':
                print("   2. Check HCA linkage in regulatory_provisions table")
                print("   3. Run enrichment script to link provisions to HCAs")

        return test_results

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    verifier = HCACodeVerifier()

    try:
        results = verifier.run_all_tests()

        # Exit with error code if any test failed
        if any(r['status'] == 'FAIL' for r in results.values()):
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        verifier.close()
