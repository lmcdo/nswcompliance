#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search ALL LEP documents for clauses that might be 4.3 or 4.4
        cur.execute("""
            SELECT
                id,
                document_id,
                ref_number,
                section_header,
                LEFT(provision_text, 200) as text_preview
            FROM regulatory_provisions
            WHERE (document_id LIKE '%Inner_West_Local_Environmental_Plan_2022%'
                   AND document_id LIKE '%NSW_Legislation%')
            AND (
                provision_text ILIKE '%height of buildings%'
                OR provision_text ILIKE '%maximum building height%'
                OR provision_text ILIKE '%floor space ratio%'
                OR section_header ILIKE '%height of buildings%'
                OR section_header ILIKE '%floor space ratio%'
            )
            LIMIT 10
        """)

        results = cur.fetchall()

        print(f"Found {len(results)} provisions about height/FSR:\n")

        for row in results:
            print(f"ID: {row[0]}")
            print(f"Document: {row[1]}")
            print(f"Clause: {row[2]}")
            print(f"Header: {row[3]}")
            print(f"Text: {row[4]}...")
            print("=" * 80 + "\n")