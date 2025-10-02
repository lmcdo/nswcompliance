#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, ref_number, section_header, provision_text
            FROM regulatory_provisions
            WHERE document_id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
            AND (ref_number LIKE '4.3%' OR ref_number LIKE '4.4%')
            ORDER BY ref_number
        """)

        results = cur.fetchall()

        print(f"Found {len(results)} clauses:\n")

        for row in results:
            print(f"ID: {row[0]}")
            print(f"Clause: {row[1]}")
            print(f"Header: {row[2] or 'No header'}")
            print(f"Full text:\n{row[3]}\n")
            print("=" * 80 + "\n")