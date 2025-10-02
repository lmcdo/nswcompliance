#!/usr/bin/env python3

import psycopg2
from psycopg2.extras import RealDictCursor

def get_real_sepp_wat():
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port='5432'
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print('=== SEARCHING FOR REAL SEPP WATER USE MAP PROVISIONS ===')

    # Search for actual SEPP water provisions
    cursor.execute('''
        SELECT
            id, ref_number, provision_text, document_id, provision_type, zone, page_number
        FROM regulatory_provisions
        WHERE document_id ILIKE '%SEPP%'
        AND (provision_text ILIKE '%water use map%'
             OR provision_text ILIKE '%water use standard%'
             OR provision_text ILIKE '%BASIX%'
             OR provision_text ILIKE '%water efficiency%'
             OR provision_text ILIKE '%sustainable buildings%')
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    ''')

    records = cursor.fetchall()

    if not records:
        print('No direct SEPP water provisions found. Searching all SEPP provisions for water...')
        cursor.execute('''
            SELECT id, ref_number, provision_text, document_id, provision_type
            FROM regulatory_provisions
            WHERE document_id ILIKE '%SEPP%'
            AND provision_text ILIKE '%water%'
            ORDER BY LENGTH(provision_text) DESC
            LIMIT 3
        ''')
        records = cursor.fetchall()

    for i, record in enumerate(records, 1):
        print(f'\n=== AUTHENTIC SEPP WATER RECORD {i} ===')
        print(f'ID: {record["id"]}')
        print(f'Reference: {record["ref_number"]}')
        print(f'Document: {record["document_id"]}')
        print(f'Type: {record["provision_type"]}')
        if "zone" in record and record["zone"]:
            print(f'Zone: {record["zone"]}')

        provision_text = record["provision_text"]
        print(f'\n--- COMPLETE PROVISION TEXT ({len(provision_text)} characters) ---')
        print(provision_text)
        print('=' * 80)

    # Also check for any WAT-specific records
    print('\n=== SEARCHING FOR WAT (Water Aptitude Test) REFERENCES ===')
    cursor.execute('''
        SELECT id, ref_number, provision_text, document_id
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%wat %'
        OR provision_text ILIKE '% wat%'
        OR ref_number ILIKE '%wat%'
        LIMIT 3
    ''')

    wat_records = cursor.fetchall()
    for record in wat_records:
        print(f'ID: {record["id"]} | Ref: {record["ref_number"]} | Doc: {record["document_id"]}')
        print(f'Text: {record["provision_text"][:200]}...')
        print('-' * 40)

    conn.close()

if __name__ == "__main__":
    get_real_sepp_wat()