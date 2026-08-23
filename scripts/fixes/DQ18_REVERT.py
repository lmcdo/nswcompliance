#!/usr/bin/env python3
"""REVERT DQ-18: The fix was WRONG.

The URL page numbers (page_5.png) are extraction sequence numbers, NOT DCP page numbers.
The original pdf_page values were correct - they matched the actual DCP page shown in documents.

This script cannot restore original values without a backup.
Instead, we need to understand what the correct values should be.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2

SUPABASE_DB = os.environ['DATABASE_URL']

def main():
    conn = psycopg2.connect(SUPABASE_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('ANALYZING MARRICKVILLE PAGE DATA')
    print('=' * 60)

    # Check if there's a consistent offset pattern
    # The original pdf_page might have been (url_page - offset)
    cur.execute("""
        SELECT
            SUBSTRING(pdf_page_image_url FROM '2_5_Equity') IS NOT NULL as is_equity,
            pdf_page,
            CAST(SUBSTRING(pdf_page_image_url FROM 'page_([0-9]+)\\.') AS INTEGER) as url_page,
            pdf_page_image_url
        FROM regulatory_provisions
        WHERE document_id LIKE '%Marrickville%'
          AND pdf_page_image_url LIKE '%2_5_Equity%'
        ORDER BY pdf_page
        LIMIT 10
    """)

    print('\nSection 2.5 Equity provisions:')
    for row in cur.fetchall():
        print(f'  pdf_page={row[1]}, url_page={row[2]}')

    # The key insight: if original pdf_page was 1 and url_page is 5,
    # then the offset was +4 (or url_page - pdf_page = 4)
    # To revert: new_pdf_page = url_page - 4 = original pdf_page

    # But wait - I SET pdf_page = url_page, so now pdf_page = 5
    # To revert to original (1), I need: pdf_page = pdf_page - 4

    # Let's check the pattern for different sections
    cur.execute("""
        SELECT
            CASE
                WHEN pdf_page_image_url LIKE '%2_5_Equity%' THEN '2.5 Equity'
                WHEN pdf_page_image_url LIKE '%2_6_Acoustic%' THEN '2.6 Acoustic'
                WHEN pdf_page_image_url LIKE '%2_10_Parking%' THEN '2.10 Parking'
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

    print('\nPage ranges by section (AFTER bad fix):')
    for row in cur.fetchall():
        print(f'  {row[0]}: pages {row[1]}-{row[2]} ({row[3]} provisions)')

    conn.close()
    print('\nNeed to determine correct offset per section to revert.')

if __name__ == '__main__':
    main()
