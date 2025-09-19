#!/usr/bin/env python3
"""
Count actual SEPP provisions in source documents
"""

import sqlite3

def count_actual_sepp():
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    print('=== SEPP DOCUMENT ANALYSIS ===')

    # Count provisions from SEPP documents
    cursor.execute('''
        SELECT COUNT(*) FROM regulatory_provisions rp
        JOIN documents d ON rp.document_id = d.id
        WHERE d.document_type = 'SEPP'
    ''')
    actual_sepp_count = cursor.fetchone()[0]
    print(f'Actual provisions from SEPP documents: {actual_sepp_count:,}')

    # Break down by SEPP type
    cursor.execute('''
        SELECT
            CASE
                WHEN d.pdf_name LIKE '%Exempt and Complying%' THEN 'Exempt and Complying'
                WHEN d.pdf_name LIKE '%Housing%' THEN 'Housing'
                ELSE 'Other'
            END as sepp_type,
            COUNT(*)
        FROM regulatory_provisions rp
        JOIN documents d ON rp.document_id = d.id
        WHERE d.document_type = 'SEPP'
        GROUP BY sepp_type
        ORDER BY COUNT(*) DESC
    ''')
    sepp_breakdown = cursor.fetchall()
    print(f'\nSEPP provisions by type:')
    for sepp_type, count in sepp_breakdown:
        print(f'  {sepp_type}: {count:,} provisions')

    # Sample SEPP provision text
    cursor.execute('''
        SELECT rp.provision_text
        FROM regulatory_provisions rp
        JOIN documents d ON rp.document_id = d.id
        WHERE d.document_type = 'SEPP'
        AND d.pdf_name LIKE '%Exempt and Complying%'
        LIMIT 3
    ''')
    samples = cursor.fetchall()
    print(f'\nSample Exempt & Complying provisions:')
    for i, (text,) in enumerate(samples, 1):
        sample_text = text[:100] + '...' if len(text) > 100 else text
        print(f'  {i}. {sample_text}')

    conn.close()

    print(f'\n=== CONCLUSION ===')
    print(f'- Total SEPP provisions in database: {actual_sepp_count:,}')
    print(f'- PRP-M2 extracted: 710 provisions')
    print(f'- Issue: PRP-M2 extraction logic missed many SEPP provisions')
    print(f'- Fix: Need to update PRP-M2 to use document_type = "SEPP" instead of text patterns')

if __name__ == "__main__":
    count_actual_sepp()