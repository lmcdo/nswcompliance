#!/usr/bin/env python3
"""REVERT DQ-18: Fix Marrickville pdf_page by subtracting section offsets.

The previous DQ18 fix was WRONG. It set pdf_page = url_page, but:
- URL page numbers are EXTRACTION SEQUENCE numbers (e.g., page_5.png = 5th page extracted)
- pdf_page should be ACTUAL DCP PAGE NUMBER (e.g., page 1 in the DCP document)

The correct formula is: pdf_page = url_page - offset
where offset varies by section (mostly 4 for Part 2 sections).
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import re
import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

# Section offsets from fix_marrickville_page_numbers.sql
SECTION_OFFSETS = {
    '2_10_Parking': 4,
    '2_11_Fencing': 4,
    '2_12_Signs_and_Advertising': 4,
    '2_13_Biodiversity': 4,
    '2_14_Unique_Environmental_': 4,
    '2_16_Energy_Efficiency': 4,
    '2_1_Urban_Design': 4,
    '2_5_Equity_of_Access_and_M': 4,
    '2_6_Acoustic_and_Visual_Pr': 4,
    '2_7_Solar_Access_and_Overs': 4,
    '2_8_Social_Impact_Assessme': 4,
    '2_9_Community_Safety': 4,
    '4.1_Low_Density_Residentia': 6,
    '4_2_Multi_Dwelling_Housing': 4,
    '4_3_Boarding_Houses': 4,
    '5_0_Commercial_and_Mixed_U': 4,
    '6_0_Industrial_Development': 4,
    '7.3_Sex_Industry_and_Adult': 4,
    '7_1_childcare_centres_-_wi': 6,
    '8.0_Heritage': -48,  # Adds 48
    '8.0_Heritage_-_Part1_(page': 14,
    '8.0_Heritage_-_Part2_(page': -48,  # Adds 48
    '8.0_Heritage_-_Part4_(page': 7,
    '2_17_Water_Sensitive_Urban': 4,
    '2_25_Stormwater_management': 4,
    '2_3_Site_Context_Analysis': 4,
    '3_0Part3Subdivision,_Amalg': 4,
}

def get_offset_for_url(url: str) -> int | None:
    """Get the offset for a given URL based on section pattern."""
    if not url:
        return None
    for pattern, offset in SECTION_OFFSETS.items():
        if pattern in url:
            return offset
    return None

def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-18 REVERT: Fix Marrickville pdf_page values')
    print('=' * 60)

    # Get all Marrickville provisions with URLs
    cur.execute("""
        SELECT id, pdf_page, pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f'\nTotal Marrickville provisions with URLs: {len(rows)}')

    # Calculate fixes
    fixes = []
    for row_id, current_page, url in rows:
        offset = get_offset_for_url(url)
        if offset is not None and current_page is not None:
            correct_page = current_page - offset
            if correct_page != current_page and correct_page > 0:
                fixes.append((row_id, current_page, correct_page, url, offset))

    print(f'Provisions to fix: {len(fixes)}')

    if not fixes:
        print('\nNo fixes needed.')
        conn.close()
        return

    # Show samples by section
    print('\nSample fixes by section:')
    sections_shown = set()
    for row_id, current, correct, url, offset in fixes[:50]:
        # Extract section from URL
        for pattern in SECTION_OFFSETS:
            if pattern in url:
                if pattern not in sections_shown:
                    sections_shown.add(pattern)
                    print(f'  {pattern}: pdf_page {current} -> {correct} (offset {offset})')
                break

    # Apply fixes
    print(f'\nApplying {len(fixes)} fixes...')
    fixed = 0
    for row_id, current_page, correct_page, url, offset in fixes:
        cur.execute("""
            UPDATE regulatory_provisions
            SET pdf_page = %s
            WHERE id = %s
        """, (correct_page, row_id))
        fixed += cur.rowcount

    conn.commit()
    print(f'Fixed {fixed} provisions')

    # Verify by section
    print('\nVerification - page ranges by section:')
    cur.execute("""
        SELECT
            CASE
                WHEN pdf_page_image_url LIKE '%2_5_Equity%' THEN '2.5 Equity'
                WHEN pdf_page_image_url LIKE '%2_6_Acoustic%' THEN '2.6 Acoustic'
                WHEN pdf_page_image_url LIKE '%2_7_Solar%' THEN '2.7 Solar'
                WHEN pdf_page_image_url LIKE '%2_8_Social%' THEN '2.8 Social'
                WHEN pdf_page_image_url LIKE '%2_10_Parking%' THEN '2.10 Parking'
                WHEN pdf_page_image_url LIKE '%2_11_Fencing%' THEN '2.11 Fencing'
                WHEN pdf_page_image_url LIKE '%2_12_Signs%' THEN '2.12 Signs'
                WHEN pdf_page_image_url LIKE '%4.1_Low_Density%' THEN '4.1 Low Density'
                WHEN pdf_page_image_url LIKE '%8.0_Heritage%' THEN '8.0 Heritage'
                ELSE 'Other'
            END as section,
            MIN(pdf_page) as min_page,
            MAX(pdf_page) as max_page,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """)

    for row in cur.fetchall():
        print(f'  {row[0]}: pages {row[1]}-{row[2]} ({row[3]} provisions)')

    conn.close()
    print('\nDone!')

if __name__ == '__main__':
    main()
