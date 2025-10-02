#!/usr/bin/env python3
"""Check for LEP provisions in database"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search for LEP provisions about height and FSR
        cur.execute("""
            SELECT
                id,
                document_id,
                ref_number,
                provision_text,
                LENGTH(provision_text) as text_length
            FROM regulatory_provisions
            WHERE (
                document_id LIKE '%Inner West%Environmental%Plan%'
                OR document_id LIKE '%LEP%'
            )
            AND (
                provision_text ILIKE '%height%building%'
                OR provision_text ILIKE '%floor space ratio%'
                OR ref_number LIKE '4.3%'
                OR ref_number LIKE '4.4%'
            )
            LIMIT 10
        """)

        results = cur.fetchall()

        print(f'Found {len(results)} LEP provisions\n')

        for row in results:
            print(f'ID: {row[0]}')
            print(f'Document: {row[1][:80]}')
            print(f'Clause: {row[2]}')
            print(f'Text length: {row[4]} chars')
            print(f'Text preview: {row[3][:150]}...')
            print('-' * 80)