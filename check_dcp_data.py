#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== DCP DATA IN POSTGRESQL ===")

    # Check for DCP references in regulatory_provisions
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%DCP%'
        OR ref_number ILIKE '%DCP%'
        OR section_header ILIKE '%DCP%'
        OR document_id ILIKE '%DCP%'
    """)
    dcp_count = cursor.fetchone()
    print(f"DCP mentions in regulatory_provisions: {dcp_count['count']}")

    # Check documents table for DCP documents
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM documents
        WHERE document_type = 'DCP'
    """)
    dcp_docs = cursor.fetchone()
    print(f"DCP documents: {dcp_docs['count']}")

    if dcp_docs['count'] > 0:
        cursor.execute("""
            SELECT id, pdf_name, document_area, char_count, word_count
            FROM documents
            WHERE document_type = 'DCP'
            ORDER BY char_count DESC
            LIMIT 10
        """)
        docs = cursor.fetchall()
        print("\nTop DCP documents by size:")
        for doc in docs:
            print(f"  {doc['id']}: {doc['pdf_name']}")
            print(f"    Area: {doc['document_area']}, Chars: {doc['char_count']}, Words: {doc['word_count']}")

    # Check for specific Inner West DCP data
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%'
        AND document_id ILIKE '%dcp%'
    """)
    iw_dcp_count = cursor.fetchone()
    print(f"\nInner West DCP provisions: {iw_dcp_count['count']}")

    if iw_dcp_count['count'] > 0:
        cursor.execute("""
            SELECT DISTINCT document_id
            FROM regulatory_provisions
            WHERE document_id ILIKE '%inner%west%'
            AND document_id ILIKE '%dcp%'
            LIMIT 5
        """)
        iw_docs = cursor.fetchall()
        print("Inner West DCP document IDs:")
        for doc in iw_docs:
            print(f"  {doc['document_id']}")

    # Sample DCP provisions
    if dcp_count['count'] > 0:
        cursor.execute("""
            SELECT ref_number, section_header, provision_text, document_id
            FROM regulatory_provisions
            WHERE provision_text ILIKE '%DCP%'
            OR ref_number ILIKE '%DCP%'
            OR document_id ILIKE '%DCP%'
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\nSample DCP provisions:")
        for sample in samples:
            text = sample['provision_text'][:200] + '...' if sample['provision_text'] and len(sample['provision_text']) > 200 else sample['provision_text']
            print(f"  {sample['ref_number']}: {sample['section_header']}")
            print(f"    Doc: {sample['document_id']}")
            print(f"    Text: {text}")
            print()

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
