#!/usr/bin/env python3
"""
Verification Script: Marrickville Zone Filtering
Purpose: Test zone-based filtering BEFORE and AFTER zone tagging fix
Date: 2026-01-29
Issue: #1 from Applicability-Based DCP Filtering Plan

Problem:
Marrickville Parts 4-6 ALL tagged with ['ALL'] instead of specific zones:
- Part 4.1 (Low Density) → should be ['R2']
- Part 4.2 (Multi-Dwelling) → should be ['R3', 'R4']
- Part 5 (Commercial) → should be ['B1', 'B2', 'B4', 'B5', 'B6']
- Part 6 (Industrial) → should be ['IN1', 'IN2', 'IN3']

Tests:
1. Check current zone tagging for Marrickville Parts 4-6
2. Verify provisions are incorrectly tagged with ['ALL']
3. Test that Layer 2 (use_specific) returns ALL provisions (before fix)
4. Provide expected counts after fix
"""

import os
import sys
from typing import Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MarrickvilleZoneVerifier:
    def __init__(self):
        self.conn = psycopg2.connect(
            host=os.getenv('PGHOST'),
            port=os.getenv('PGPORT'),
            database=os.getenv('PGDATABASE'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD')
        )
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

    def test_current_zone_tagging(self) -> Dict:
        """Check current zone tagging for Marrickville Parts 4-6"""
        print("\n" + "="*80)
        print("TEST 1: Current Zone Tagging for Marrickville Parts 4-6")
        print("="*80)

        parts_to_check = [
            ('Part 4.1', 'Part 4.1 Low Density Residential Development'),
            ('Part 4.2', 'Part 4.2 Multi-Dwelling Housing Development'),
            ('Part 5', 'Part 5 Commercial and Mixed Use Development'),
            ('Part 6', 'Part 6 Industrial Development')
        ]

        results = {}

        for part_num, part_name in parts_to_check:
            query = """
            SELECT
                COUNT(*) as total_provisions,
                COUNT(*) FILTER (WHERE v2_applicable_zones = ARRAY['ALL']) as tagged_all,
                COUNT(*) FILTER (WHERE v2_applicable_zones != ARRAY['ALL']) as tagged_specific,
                array_agg(DISTINCT v2_applicable_zones) as unique_zone_tags
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Marrickville%'
              AND v2_dcp_part = %s
              AND v2_is_actionable = true;
            """

            self.cursor.execute(query, (part_num,))
            result = self.cursor.fetchone()

            print(f"\n{part_name}:")
            print(f"   Total provisions: {result['total_provisions']}")
            print(f"   Tagged ['ALL']: {result['tagged_all']}")
            print(f"   Tagged specific zones: {result['tagged_specific']}")
            print(f"   Unique zone tags: {result['unique_zone_tags']}")

            results[part_num] = dict(result)

            # Check if ALL are tagged with ['ALL']
            if result['tagged_all'] == result['total_provisions']:
                print(f"   ❌ INCORRECT: All provisions tagged ['ALL'] (should have specific zones)")
            else:
                print(f"   ✅ CORRECT: Provisions have specific zone tags")

        return results

    def test_expected_zone_mappings(self) -> Dict:
        """Show what zone mappings SHOULD be applied"""
        print("\n" + "="*80)
        print("TEST 2: Expected Zone Mappings (After Fix)")
        print("="*80)

        expected_mappings = {
            'Part 4.1': {
                'name': 'Low Density Residential Development',
                'expected_zones': ['R2'],
                'rationale': 'Part 4.1 title specifies low density (R2 zone)'
            },
            'Part 4.2': {
                'name': 'Multi-Dwelling Housing Development',
                'expected_zones': ['R3', 'R4'],
                'rationale': 'Part 4.2 multi-dwelling allowed in R3/R4 zones'
            },
            'Part 5': {
                'name': 'Commercial and Mixed Use Development',
                'expected_zones': ['B1', 'B2', 'B4', 'B5', 'B6'],
                'rationale': 'Part 5 applies to all commercial zones'
            },
            'Part 6': {
                'name': 'Industrial Development',
                'expected_zones': ['IN1', 'IN2', 'IN3'],
                'rationale': 'Part 6 applies to all industrial zones'
            }
        }

        print("\nExpected zone mappings:\n")

        for part, mapping in expected_mappings.items():
            print(f"{part} - {mapping['name']}")
            print(f"   Expected zones: {mapping['expected_zones']}")
            print(f"   Rationale: {mapping['rationale']}")
            print()

        return expected_mappings

    def test_layer_2_filter_simulation(self, zone: str) -> Dict:
        """Simulate Layer 2 (use_specific) filtering for a given zone"""
        print("\n" + "="*80)
        print(f"TEST 3: Layer 2 Filtering Simulation (Zone: {zone})")
        print("="*80)

        # Current behavior: Zone filter with 'ALL' tags
        query_current = """
        SELECT
            v2_dcp_part,
            COUNT(*) as provision_count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_layer = 'use_specific'
          AND v2_is_actionable = true
          AND (%s = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))
        GROUP BY v2_dcp_part
        ORDER BY v2_dcp_part;
        """

        self.cursor.execute(query_current, (zone,))
        current_results = self.cursor.fetchall()

        print(f"\nCURRENT BEHAVIOR (with ['ALL'] tags):")
        print(f"Zone {zone} gets provisions from:\n")

        total_current = 0
        for row in current_results:
            print(f"   {row['v2_dcp_part']:15s}: {row['provision_count']:4d} provisions")
            total_current += row['provision_count']

        print(f"\nTotal provisions: {total_current}")

        # Expected behavior after fix (manually determine which parts should match)
        zone_to_parts = {
            'R2': ['Part 4.1'],
            'R3': ['Part 4.2'],
            'R4': ['Part 4.2'],
            'B1': ['Part 5'],
            'B2': ['Part 5'],
            'B4': ['Part 5'],
            'B5': ['Part 5'],
            'B6': ['Part 5'],
            'IN1': ['Part 6'],
            'IN2': ['Part 6'],
            'IN3': ['Part 6']
        }

        expected_parts = zone_to_parts.get(zone, [])

        print(f"\n\nEXPECTED BEHAVIOR (after zone tagging fix):")
        print(f"Zone {zone} should ONLY get provisions from: {expected_parts}")

        if current_results and expected_parts:
            current_parts = [row['v2_dcp_part'] for row in current_results]

            extra_parts = [p for p in current_parts if p not in expected_parts]

            if extra_parts:
                print(f"\n❌ INCORRECT: Currently getting provisions from extra parts: {extra_parts}")
                print(f"   This is because all parts are tagged ['ALL']")
            else:
                print(f"\n✅ CORRECT: Already filtering correctly")

        return {
            'zone': zone,
            'current_provision_count': total_current,
            'current_parts': [dict(r) for r in current_results],
            'expected_parts': expected_parts
        }

    def test_all_common_zones(self) -> Dict:
        """Test filtering for all common zones"""
        print("\n" + "="*80)
        print("TEST 4: All Common Zones")
        print("="*80)

        common_zones = ['R2', 'R3', 'B1', 'IN1']

        results = {}

        for zone in common_zones:
            results[zone] = self.test_layer_2_filter_simulation(zone)

        return results

    def calculate_fix_impact(self) -> Dict:
        """Calculate impact of zone tagging fix"""
        print("\n" + "="*80)
        print("TEST 5: Fix Impact Analysis")
        print("="*80)

        # Total provisions that will be retagged
        query = """
        SELECT
            v2_dcp_part,
            COUNT(*) as provision_count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part IN ('Part 4.1', 'Part 4.2', 'Part 5', 'Part 6')
          AND v2_is_actionable = true
        GROUP BY v2_dcp_part
        ORDER BY v2_dcp_part;
        """

        self.cursor.execute(query)
        parts = self.cursor.fetchall()

        print("\nProvisions to be retagged:\n")

        total = 0
        for row in parts:
            print(f"   {row['v2_dcp_part']:15s}: {row['provision_count']:4d} provisions")
            total += row['provision_count']

        print(f"\nTotal provisions affected: {total}")

        print("\n\nExpected changes:")
        print("   - Part 4.1 (91) → zone = ['R2']")
        print("   - Part 4.2 (31) → zone = ['R3', 'R4']")
        print("   - Part 5 (60) → zone = ['B1', 'B2', 'B4', 'B5', 'B6']")
        print("   - Part 6 (58) → zone = ['IN1', 'IN2', 'IN3']")

        print("\n\nImpact on API responses:")
        print("   BEFORE: R2 property gets ~240 provisions (Parts 4.1 + 4.2 + 5 + 6)")
        print("   AFTER:  R2 property gets ~91 provisions (Part 4.1 only)")
        print("   Reduction: ~149 irrelevant provisions (62% reduction)")

        return {
            'total_provisions_affected': total,
            'parts': [dict(r) for r in parts]
        }

    def run_all_tests(self):
        """Run all verification tests"""
        print("\n" + "█"*80)
        print(" MARRICKVILLE ZONE FILTERING VERIFICATION")
        print("█"*80)

        test_results = {
            'test_1_current_tagging': self.test_current_zone_tagging(),
            'test_2_expected_mappings': self.test_expected_zone_mappings(),
            'test_3_all_zones': self.test_all_common_zones(),
            'test_4_fix_impact': self.calculate_fix_impact()
        }

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        # Check if any parts have specific zone tags
        current_tagging = test_results['test_1_current_tagging']

        all_incorrect = all(
            result['tagged_all'] == result['total_provisions']
            for result in current_tagging.values()
        )

        if all_incorrect:
            print("\n❌ ALL PARTS INCORRECTLY TAGGED WITH ['ALL']")
            print("   Zone filtering will NOT work correctly")
            print("   Layer 2 (use_specific) returns all provisions regardless of zone")
            print("\n✅ READY TO APPLY FIX")
            print("   Run: scripts/enrichment/enrich_marrickville_zone_tagging.py")
        else:
            print("\n✅ SOME PARTS ALREADY HAVE SPECIFIC ZONE TAGS")
            print("   Zone filtering may already be working")

        print("\n\n📋 NEXT STEPS:")
        print("   1. Review expected zone mappings (Test 2)")
        print("   2. Run enrichment script to apply zone tags")
        print("   3. Re-run this verification to confirm fix")
        print("   4. Test API with different zones to verify filtering")

        return test_results

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    verifier = MarrickvilleZoneVerifier()

    try:
        results = verifier.run_all_tests()
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        verifier.close()
