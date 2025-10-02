#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search all LEP documents for provisions about height
        cur.execute("""
            SELECT
                document_id,
                ref_number,
                section_header,
                LENGTH(provision_text),
                LEFT(provision_text, 200)
            FROM regulatory_provisions
            WHERE document_id LIKE '%Inner_West_Local_Environmental_Plan_2022%'
            AND (
                provision_text ILIKE '%maximum%height%'
                OR provision_text ILIKE '%building%height%'
                OR ref_number = '4.3'
            )
            ORDER BY document_id, ref_number
            LIMIT 10
        """)

        results = cur.fetchall()
        print(f"Found {len(results)} provisions about height:\n")

        for row in results:
            print(f"Document: {row[0]}")
            print(f"Ref: {row[1]}")
            print(f"Header: {row[2]}")
            print(f"Text length: {row[3]} chars")
            print(f"Preview: {row[4]}")
            print("=" * 80 + "\n")