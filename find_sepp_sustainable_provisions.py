#!/usr/bin/env python3
"""
Find SEPP Sustainable Buildings provisions in database
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search for SEPP Sustainable Buildings provisions
        cur.execute("""
            SELECT
                id,
                document_id,
                ref_number,
                provision_text,
                LENGTH(provision_text) as text_length
            FROM regulatory_provisions
            WHERE document_id LIKE '%Sustainable%Buildings%'
            AND (
                provision_text ILIKE '%basix%'
                OR provision_text ILIKE '%climate%'
                OR provision_text ILIKE '%water%'
            )
            LIMIT 10
        """)

        results = cur.fetchall()

        print(f'Found {len(results)} provisions for SEPP Sustainable Buildings\n')

        for row in results:
            print(f'ID: {row[0]}')
            print(f'Document: {row[1]}')
            print(f'Clause: {row[2]}')
            print(f'Text length: {row[4]} chars')
            print(f'Text preview: {row[3][:200]}...')
            print('-' * 80)

        # Also check what document IDs exist for Sustainable Buildings
        print('\n\nAll Sustainable Buildings document IDs:')
        cur.execute("""
            SELECT DISTINCT document_id, COUNT(*) as provision_count
            FROM regulatory_provisions
            WHERE document_id LIKE '%Sustainable%Buildings%'
            GROUP BY document_id
        """)

        for doc_id, count in cur.fetchall():
            print(f'  {doc_id}: {count} provisions')