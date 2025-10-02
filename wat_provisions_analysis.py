#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def analyze_wat_provisions():
    """Detailed analysis of WAT provisions in the database"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            database='nsw_planning',
            user='postgres',
            password='postgres',
            port='5432'
        )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print('=== DETAILED WAT PROVISIONS ANALYSIS ===')
            print()

            # 1. Get all WAT-related provisions
            cur.execute("""
                SELECT document_id, provision_type, ref_number, provision_text, section_header
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%WAT%'
                OR provision_text ILIKE '%water use%'
                OR provision_text ILIKE '%water efficiency%'
                OR provision_text ILIKE '%water sensitive%'
                OR provision_text ILIKE '%BASIX water%'
                ORDER BY
                    CASE WHEN provision_text ILIKE '%WAT%' THEN 1 ELSE 2 END,
                    document_id,
                    ref_number
                LIMIT 50
            """)

            wat_provisions = cur.fetchall()

            print(f'Found {len(wat_provisions)} WAT-related provisions')
            print()

            for i, prov in enumerate(wat_provisions, 1):
                print(f'--- WAT Provision {i} ---')
                print(f'Document: {prov["document_id"]}')
                print(f'Type: {prov["provision_type"]}')
                print(f'Reference: {prov["ref_number"]}')
                print(f'Section: {prov["section_header"]}')
                print(f'Text: {prov["provision_text"][:300]}...')
                print('-' * 80)
                print()

            # 2. Analyze by document
            cur.execute("""
                SELECT document_id, COUNT(*) as wat_provision_count
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%WAT%'
                OR provision_text ILIKE '%water%'
                GROUP BY document_id
                ORDER BY wat_provision_count DESC
                LIMIT 20
            """)

            documents = cur.fetchall()

            print('=== WAT PROVISIONS BY DOCUMENT ===')
            for doc in documents:
                print(f'{doc["document_id"]}: {doc["wat_provision_count"]} provisions')
            print()

            # 3. Specific Water Use Map provisions
            cur.execute("""
                SELECT *
                FROM regulatory_provisions
                WHERE provision_text ILIKE '%Water Use Map%'
                AND provision_text ILIKE '%percentage%'
                ORDER BY document_id
                LIMIT 10
            """)

            water_map_provisions = cur.fetchall()

            print('=== WATER USE MAP SPECIFIC PROVISIONS ===')
            for i, prov in enumerate(water_map_provisions, 1):
                print(f'--- Water Use Map Provision {i} ---')
                print(f'Document: {prov["document_id"]}')
                print(f'Reference: {prov["ref_number"]}')
                print(f'Type: {prov["provision_type"]}')
                print(f'Text: {prov["provision_text"]}')
                print('-' * 80)
                print()

            # 4. SEPP Sustainable Buildings WAT provisions
            cur.execute("""
                SELECT *
                FROM regulatory_provisions
                WHERE document_id ILIKE '%Sustainable_Buildings%'
                AND (provision_text ILIKE '%WAT%' OR provision_text ILIKE '%water%')
                ORDER BY ref_number
                LIMIT 15
            """)

            sepp_wat_provisions = cur.fetchall()

            print('=== SEPP SUSTAINABLE BUILDINGS WAT PROVISIONS ===')
            for i, prov in enumerate(sepp_wat_provisions, 1):
                print(f'--- SEPP WAT Provision {i} ---')
                print(f'Reference: {prov["ref_number"]}')
                print(f'Type: {prov["provision_type"]}')
                print(f'Text: {prov["provision_text"][:200]}...')
                print()

            print(f'Total SEPP Sustainable Buildings WAT provisions: {len(sepp_wat_provisions)}')

    except Exception as e:
        print(f'Database error: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    analyze_wat_provisions()