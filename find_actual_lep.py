#!/usr/bin/env python3
"""Find actual LEP provisions for Inner West"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # First, find what LEP documents we have
        print("=== Looking for Inner West LEP documents ===\n")
        cur.execute("""
            SELECT DISTINCT document_id, COUNT(*) as provision_count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner%West%LEP%'
            OR document_id ILIKE '%Inner%West%Local%Environmental%Plan%'
            GROUP BY document_id
            ORDER BY provision_count DESC
        """)

        docs = cur.fetchall()
        print(f"Found {len(docs)} LEP documents:\n")
        for doc, count in docs:
            print(f"  {doc}: {count} provisions")

        if docs:
            # Search for clause 4.3 and 4.4 in the main LEP
            main_doc = docs[0][0]
            print(f"\n\n=== Searching in {main_doc} ===\n")

            cur.execute("""
                SELECT
                    id,
                    ref_number,
                    section_header,
                    provision_text,
                    LENGTH(provision_text) as text_length
                FROM regulatory_provisions
                WHERE document_id = %s
                AND (ref_number = '4.3' OR ref_number = '4.4'
                     OR ref_number LIKE '4.3 %' OR ref_number LIKE '4.4 %')
                ORDER BY ref_number
            """, (main_doc,))

            results = cur.fetchall()

            print(f"Found {len(results)} provisions for clauses 4.3/4.4:\n")

            for row in results:
                print(f'Clause: {row[1]}')
                print(f'Header: {row[2]}')
                print(f'Text length: {row[4]} chars')
                print(f'Full text:\n{row[3][:500]}...\n')
                print('=' * 80 + '\n')