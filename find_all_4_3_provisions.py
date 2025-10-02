#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, ref_number, section_header, LENGTH(provision_text), LEFT(provision_text, 100)
            FROM regulatory_provisions
            WHERE document_id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
            AND (ref_number = '4.3' OR ref_number LIKE '4.3.%' OR ref_number LIKE '4.3 %')
            ORDER BY ref_number
            LIMIT 20
        """)

        results = cur.fetchall()
        print(f"Found {len(results)} provisions for clause 4.3:\n")

        for row in results:
            print(f"Ref: {row[1]}")
            print(f"Header: {row[2]}")
            print(f"Text length: {row[3]} chars")
            print(f"Preview: {row[4]}")
            print("=" * 80 + "\n")