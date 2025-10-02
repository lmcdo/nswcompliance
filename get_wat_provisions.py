#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def get_wat_provisions():
    """Get all WAT provisions from database"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== WAT PROVISIONS FROM DATABASE ===\n')

            cur.execute("""
                SELECT document_id, provision_type, ref_number, provision_text, section_header
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%WAT%'
                OR provision_text ILIKE '%water use map%'
                OR provision_text ILIKE '%water use standard%'
                ORDER BY ref_number
                LIMIT 15
            """)

            provisions = cur.fetchall()

            for i, prov in enumerate(provisions, 1):
                print(f"--- WAT Provision {i} ---")
                print(f"Document: {prov['document_id']}")
                print(f"Type: {prov['provision_type']}")
                print(f"Reference: {prov['ref_number']}")
                print(f"Section: {prov['section_header']}")
                print(f"Text: {prov['provision_text']}")
                print("-" * 80)
                print()

            print(f"Total WAT provisions found: {len(provisions)}")

    except Exception as e:
        print(f'Database error: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    get_wat_provisions()