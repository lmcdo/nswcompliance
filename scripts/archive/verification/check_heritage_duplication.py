#!/usr/bin/env python3
"""
Verification Script: Heritage Provision Duplication Check
Purpose: Verify that heritage provisions don't appear multiple times across layers
Date: 2026-01-29
Issue: #2 from Applicability-Based DCP Filtering Plan

Problem:
Heritage provisions can appear in 3 layers:
- Layer 1 (Generic): Heritage provisions in generic controls (NOT filtered out)
- Layer 3 (Condition): Dedicated heritage layer (primary HCA source)
- Layer 4 (Precinct): Heritage-tagged precinct provisions (NOT filtered by heritage flag)

Tests:
1. Find provisions appearing in multiple layers (same text, different layers)
2. Check if deduplication logic catches these (by provision ID or text)
3. Test actual API response for 185 Parramatta Rd (C35 HCA)
4. Verify no duplicate heritage text in final output
"""

import os
import sys
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from collections import defaultdict

# Load environment variables
load_dotenv()

class HeritageDuplicationChecker:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT'),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD')
        )
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def test_provisions_across_layers(self) -> Dict:
        """Find heritage provisions appearing in multiple layers"""
        print("\n" + "="*80)
        print("TEST 1: Heritage Provisions Across Multiple Layers")
        print("="*80)

        query = """
        SELECT
            left(provision_text, 100) as text_preview,
            array_agg(DISTINCT v2_dcp_layer) as layers,
            array_agg(DISTINCT id) as provision_ids,
            COUNT(DISTINCT v2_dcp_layer) as layer_count,
            array_agg(DISTINCT v2_dcp_part) as parts
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
        GROUP BY left(provision_text, 100)
        HAVING COUNT(DISTINCT v2_dcp_layer) > 1
        ORDER BY layer_count DESC
        LIMIT 20;
        """

        self.cursor.execute(query)
        duplicates = self.cursor.fetchall()

        if duplicates:
            print(f"❌ Found {len(duplicates)} heritage provisions appearing in multiple layers:\n")

            for dup in duplicates[:10]:  # Show first 10
                print(f"Text: {dup['text_preview']}...")
                print(f"   Layers: {dup['layers']}")
                print(f"   Parts: {dup['parts']}")
                print(f"   Provision IDs: {dup['provision_ids']}")
                print()

            return {
                'status': 'WARN',
                'count': len(duplicates),
                'duplicates': [dict(d) for d in duplicates]
            }
        else:
            print("✅ PASS: No heritage provisions appear in multiple layers")
            return {'status': 'PASS', 'count': 0, 'duplicates': []}

    def test_exact_duplicate_ids(self) -> Dict:
        """Check for provisions with identical IDs across layers (should be impossible)"""
        print("\n" + "="*80)
        print("TEST 2: Exact Duplicate Provision IDs")
        print("="*80)

        query = """
        SELECT
            id,
            COUNT(*) as count,
            array_agg(DISTINCT v2_dcp_layer) as layers
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
        GROUP BY id
        HAVING COUNT(*) > 1;
        """

        self.cursor.execute(query)
        exact_duplicates = self.cursor.fetchall()

        if exact_duplicates:
            print(f"❌ FAIL: Found {len(exact_duplicates)} provisions with duplicate IDs")
            print("   This should be impossible - database integrity issue!")

            for dup in exact_duplicates[:5]:
                print(f"   ID: {dup['id']} appears {dup['count']} times in layers {dup['layers']}")

            return {'status': 'FAIL', 'count': len(exact_duplicates)}
        else:
            print("✅ PASS: No duplicate provision IDs (as expected)")
            return {'status': 'PASS', 'count': 0}

    def test_text_similarity_dedup(self) -> Dict:
        """Check if similar texts with first 100 chars match exist"""
        print("\n" + "="*80)
        print("TEST 3: Text Similarity Deduplication (First 100 Chars)")
        print("="*80)

        # This mimics the deduplication logic in route.ts (lines 206-246)
        query = """
        SELECT
            left(provision_text, 100) as text_key,
            page_number,
            COUNT(*) as provision_count,
            array_agg(id) as provision_ids,
            array_agg(DISTINCT v2_dcp_layer) as layers
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
        GROUP BY left(provision_text, 100), page_number
        HAVING COUNT(*) > 1
        ORDER BY provision_count DESC
        LIMIT 10;
        """

        self.cursor.execute(query)
        text_duplicates = self.cursor.fetchall()

        if text_duplicates:
            print(f"Found {len(text_duplicates)} cases of matching text (first 100 chars) + page:\n")

            for dup in text_duplicates:
                print(f"Text: {dup['text_key']}...")
                print(f"   Page: {dup['page_number']}")
                print(f"   Count: {dup['provision_count']}")
                print(f"   Layers: {dup['layers']}")
                print(f"   Provision IDs: {dup['provision_ids']}")
                print()

            print("✅ INFO: These SHOULD be caught by deduplication logic in route.ts")
            print("   Deduplication key: text.slice(0,100) + page")

            return {
                'status': 'INFO',
                'count': len(text_duplicates),
                'duplicates': [dict(d) for d in text_duplicates]
            }
        else:
            print("✅ PASS: No matching text+page combinations found")
            return {'status': 'PASS', 'count': 0}

    def test_heritage_layer_distribution(self) -> Dict:
        """Show distribution of heritage provisions across layers"""
        print("\n" + "="*80)
        print("TEST 4: Heritage Provision Layer Distribution")
        print("="*80)

        query = """
        SELECT
            v2_dcp_layer,
            COUNT(*) as provision_count,
            COUNT(DISTINCT v2_dcp_part) as part_count,
            array_agg(DISTINCT v2_dcp_part) as parts
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
        GROUP BY v2_dcp_layer
        ORDER BY v2_dcp_layer;
        """

        self.cursor.execute(query)
        distribution = self.cursor.fetchall()

        print("Heritage provisions by layer:\n")

        for layer in distribution:
            print(f"{layer['v2_dcp_layer']:15s}: {layer['provision_count']:4d} provisions")
            print(f"                   Parts: {layer['parts']}")
            print()

        # Check if Layer 1 (generic) has heritage provisions (potential duplication source)
        layer_1_count = next((d['provision_count'] for d in distribution if d['v2_dcp_layer'] == 'generic'), 0)
        layer_3_count = next((d['provision_count'] for d in distribution if d['v2_dcp_layer'] == 'condition'), 0)
        layer_4_count = next((d['provision_count'] for d in distribution if d['v2_dcp_layer'] == 'precinct'), 0)

        print(f"Layer 1 (Generic): {layer_1_count} heritage provisions")
        print(f"Layer 3 (Condition): {layer_3_count} heritage provisions")
        print(f"Layer 4 (Precinct): {layer_4_count} heritage provisions")

        if layer_1_count > 0 and layer_3_count > 0:
            print("\n⚠️  WARNING: Heritage provisions in BOTH Layer 1 (generic) and Layer 3 (condition)")
            print("   Risk of duplication if same provisions appear in both layers")

        return {
            'status': 'INFO',
            'distribution': [dict(d) for d in distribution],
            'layer_1_count': layer_1_count,
            'layer_3_count': layer_3_count,
            'layer_4_count': layer_4_count
        }

    def test_api_response_deduplication(self, api_url: str = "http://localhost:3003") -> Dict:
        """Test actual API response for duplicate heritage provisions"""
        print("\n" + "="*80)
        print("TEST 5: API Response Deduplication (185 Parramatta Rd)")
        print("="*80)

        # Test parameters for 185 Parramatta Rd, Annandale
        params = {
            'lga': 'Inner West',
            'former_council': 'Leichhardt',
            'zone': 'R1',
            'heritage': 'true',
            'hca': 'C35',
            'topic': 'heritage'
        }

        endpoint = f"{api_url}/api/provisions/for-property"

        print(f"Testing: {endpoint}")
        print(f"Params: {params}\n")

        try:
            response = requests.get(endpoint, params=params, timeout=30)

            if response.status_code != 200:
                print(f"❌ API returned status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return {'status': 'FAIL', 'error': f"Status {response.status_code}"}

            data = response.json()

            # Check for duplicates in response
            provisions = []

            # Extract provisions from all layers
            if 'by_toc' in data:
                for part_group in data['by_toc']:
                    if 'sections' in part_group:
                        for section in part_group['sections']:
                            if 'provisions' in section:
                                provisions.extend(section['provisions'])

            print(f"Total provisions in response: {len(provisions)}")

            # Check for duplicate IDs
            ids = [p['id'] for p in provisions]
            duplicate_ids = [id for id in ids if ids.count(id) > 1]

            if duplicate_ids:
                print(f"❌ FAIL: Found {len(set(duplicate_ids))} duplicate provision IDs in API response")
                print(f"   Duplicate IDs: {set(duplicate_ids)}")
                return {'status': 'FAIL', 'duplicate_ids': list(set(duplicate_ids))}

            # Check for duplicate text (first 100 chars)
            text_keys = defaultdict(list)
            for p in provisions:
                text_key = p.get('provision_text', '')[:100] + str(p.get('page_number', ''))
                text_keys[text_key].append(p['id'])

            duplicate_texts = {k: v for k, v in text_keys.items() if len(v) > 1}

            if duplicate_texts:
                print(f"❌ FAIL: Found {len(duplicate_texts)} duplicate text+page combinations")
                print("\nExamples:")
                for text_key, ids in list(duplicate_texts.items())[:3]:
                    print(f"   Text: {text_key[:80]}...")
                    print(f"   IDs: {ids}")
                return {'status': 'FAIL', 'duplicate_texts': len(duplicate_texts)}

            print("✅ PASS: No duplicates found in API response")
            print("   Deduplication logic is working correctly")

            return {
                'status': 'PASS',
                'total_provisions': len(provisions),
                'unique_ids': len(set(ids))
            }

        except requests.exceptions.ConnectionError:
            print("⚠️  SKIP: API not running (run 'npm run dev' in frontend-nextjs)")
            return {'status': 'SKIP', 'error': 'Connection refused'}

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return {'status': 'ERROR', 'error': str(e)}

    def run_all_tests(self, test_api: bool = True):
        """Run all verification tests"""
        print("\n" + "█"*80)
        print(" HERITAGE PROVISION DUPLICATION CHECK")
        print("█"*80)

        test_results = {
            'test_1_provisions_across_layers': self.test_provisions_across_layers(),
            'test_2_exact_duplicate_ids': self.test_exact_duplicate_ids(),
            'test_3_text_similarity_dedup': self.test_text_similarity_dedup(),
            'test_4_layer_distribution': self.test_heritage_layer_distribution()
        }

        if test_api:
            test_results['test_5_api_response'] = self.test_api_response_deduplication()

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        passed = sum(1 for r in test_results.values() if r['status'] == 'PASS')
        failed = sum(1 for r in test_results.values() if r['status'] == 'FAIL')
        warnings = sum(1 for r in test_results.values() if r['status'] in ['WARN', 'INFO'])
        skipped = sum(1 for r in test_results.values() if r['status'] == 'SKIP')

        print(f"\nTests Passed: {passed}")
        print(f"Tests Failed: {failed}")
        print(f"Warnings/Info: {warnings}")
        print(f"Skipped: {skipped}")

        if failed == 0:
            print("\n✅ NO CRITICAL ISSUES - Deduplication appears to be working")

            if warnings > 0:
                print("⚠️  Some provisions appear in multiple layers, but should be caught by deduplication")
        else:
            print("\n❌ CRITICAL ISSUES FOUND - Deduplication may not be working correctly")

            # Recommendations
            print("\n📋 RECOMMENDATIONS:")

            if test_results['test_1_provisions_across_layers']['status'] == 'WARN':
                print("   1. Review provisions appearing in multiple layers")
                print("   2. Verify deduplication logic in route.ts catches these cases")

            if test_results['test_2_exact_duplicate_ids']['status'] == 'FAIL':
                print("   3. Database integrity issue - same provision ID appearing multiple times")
                print("   4. Run database cleanup to remove exact duplicates")

            if test_api and test_results.get('test_5_api_response', {}).get('status') == 'FAIL':
                print("   5. API deduplication not working - review route.ts lines 206-246")

        return test_results

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Check for heritage provision duplication')
    parser.add_argument('--no-api', action='store_true', help='Skip API testing')
    args = parser.parse_args()

    checker = HeritageDuplicationChecker()

    try:
        results = checker.run_all_tests(test_api=not args.no_api)

        # Exit with error code if any test failed (not warnings)
        if any(r['status'] == 'FAIL' for r in results.values()):
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        checker.close()
