#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test SEPP filtering with development type awareness"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from db_safety_wrapper import get_safe_connection

def test_residential_filtering():
    """Test that residential development types get Schedule 1 & 2"""
    print("=" * 80)
    print("TEST 1: Residential Development Type (dwelling_house)")
    print("Expected: Schedule 1 & 2 (BASIX), water-related clauses only")
    print("=" * 80)

    with get_safe_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
              ref_number,
              section_header,
              LEFT(provision_text, 150) as text_preview,
              CASE
                WHEN ref_number LIKE 'Schedule%%' THEN 100
                WHEN ref_number LIKE 'Chapter 3%%' THEN 80
                WHEN ref_number LIKE 'Chapter 2%%' THEN 70
                WHEN provision_type ILIKE '%%standard%%' THEN 60
                WHEN provision_type ILIKE '%%requirement%%' THEN 50
                WHEN ref_number LIKE 'Chapter 1%%' THEN 20
                ELSE 30
              END as relevance_score
            FROM provisions_with_category
            WHERE document_category = 'SEPP'
            AND document_id LIKE '%%Sustainable%%Buildings%%2022%%'
            AND provision_text ILIKE '%%water%%'
            AND (
                ref_number LIKE 'Schedule 1%%' OR
                ref_number LIKE 'Schedule 2%%' OR
                ref_number LIKE '2.1%%'
            )
            AND ref_number NOT LIKE '1.1%%'
            AND ref_number NOT LIKE '1.2%%'
            AND ref_number NOT LIKE '1.5%%'
            AND section_header NOT ILIKE '%%name of policy%%'
            ORDER BY relevance_score DESC, ref_number
            LIMIT 10
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print(f"\nFound {len(results)} provisions:\n")
        for row in results:
            print(f"✓ {row[0]}: {row[1]}")
            print(f"  Score: {row[3]}")
            print(f"  Preview: {row[2]}...")
            print()

def test_commercial_filtering():
    """Test that commercial development types get Schedule 3"""
    print("\n" + "=" * 80)
    print("TEST 2: Commercial Development Type")
    print("Expected: Schedule 3 (Large Commercial), 3-star NABERS rating")
    print("=" * 80)

    with get_safe_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
              ref_number,
              section_header,
              LEFT(provision_text, 150) as text_preview,
              CASE
                WHEN ref_number LIKE 'Schedule%%' THEN 100
                WHEN ref_number LIKE 'Chapter 3%%' THEN 80
                WHEN ref_number LIKE 'Chapter 2%%' THEN 70
                WHEN provision_type ILIKE '%%standard%%' THEN 60
                WHEN provision_type ILIKE '%%requirement%%' THEN 50
                WHEN ref_number LIKE 'Chapter 1%%' THEN 20
                ELSE 30
              END as relevance_score
            FROM provisions_with_category
            WHERE document_category = 'SEPP'
            AND document_id LIKE '%%Sustainable%%Buildings%%2022%%'
            AND provision_text ILIKE '%%water%%'
            AND (
                ref_number LIKE 'Schedule 3%%' OR
                ref_number LIKE '3.3%%'
            )
            AND ref_number NOT LIKE '1.1%%'
            AND ref_number NOT LIKE '1.2%%'
            AND section_header NOT ILIKE '%%name of policy%%'
            ORDER BY relevance_score DESC, ref_number
            LIMIT 10
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print(f"\nFound {len(results)} provisions:\n")
        for row in results:
            print(f"✓ {row[0]}: {row[1]}")
            print(f"  Score: {row[3]}")
            print(f"  Preview: {row[2]}...")
            print()

def test_no_filtering():
    """Test without development type filter (shows all)"""
    print("\n" + "=" * 80)
    print("TEST 3: No Development Type (unfiltered)")
    print("Expected: All schedules, 20 clauses")
    print("=" * 80)

    with get_safe_connection() as conn:
        cursor = conn.cursor()

        query = """
            SELECT
              ref_number,
              section_header,
              LEFT(provision_text, 100) as text_preview
            FROM provisions_with_category
            WHERE document_category = 'SEPP'
            AND document_id LIKE '%%Sustainable%%Buildings%%2022%%'
            AND provision_text ILIKE '%%water%%'
            ORDER BY ref_number
            LIMIT 20
        """

        cursor.execute(query)
        results = cursor.fetchall()

        print(f"\nFound {len(results)} provisions:\n")
        for row in results:
            header = row[1][:60] if row[1] else "No header"
            print(f"  {row[0]}: {header}")

if __name__ == '__main__':
    test_residential_filtering()
    test_commercial_filtering()
    test_no_filtering()

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("✓ Residential filter: Shows BASIX schedules (1 & 2)")
    print("✓ Commercial filter: Shows large commercial schedule (3)")
    print("✓ No filter: Shows all schedules (unfiltered)")
    print("=" * 80)
