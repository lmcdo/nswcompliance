#!/usr/bin/env python3
"""Get LEP clauses 4.3 and 4.4"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search in section 4 document
        cur.execute("""
            SELECT
                id,
                ref_number,
                section_header,
                provision_text
            FROM regulatory_provisions
            WHERE document_id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_section_4'
            AND (ref_number = '4.3' OR ref_number = '4.4')
            ORDER BY ref_number
        """)

        results = cur.fetchall()

        print(f"Found {len(results)} provisions:\n")

        for row in results:
            print(f"ID: {row[0]}")
            print(f"Clause: {row[1]}")
            print(f"Header: {row[2]}")
            print(f"Text:\n{row[3]}\n")
            print("=" * 80 + "\n")