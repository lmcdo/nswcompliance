#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== SEPP DATA IN REGULATORY PROVISIONS ===")

    # Check for SEPP references in provision_text
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%SEPP%'
        OR ref_number ILIKE '%SEPP%'
        OR section_header ILIKE '%SEPP%'
    """)
    sepp_count = cursor.fetchone()
    print(f"SEPP mentions in regulatory_provisions: {sepp_count['count']}")

    if sepp_count['count'] > 0:
        cursor.execute("""
            SELECT ref_number, section_header, provision_text, document_id
            FROM regulatory_provisions
            WHERE provision_text ILIKE '%SEPP%'
            OR ref_number ILIKE '%SEPP%'
            OR section_header ILIKE '%SEPP%'
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\nSample SEPP provisions:")
        for sample in samples:
            text = sample['provision_text'][:200] + '...' if sample['provision_text'] and len(sample['provision_text']) > 200 else sample['provision_text']
            print(f"  {sample['ref_number']}: {sample['section_header']}")
            print(f"    Doc: {sample['document_id']}")
            print(f"    Text: {text}")
            print()

    # Check documents table for SEPP docs
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM documents
        WHERE document_name ILIKE '%SEPP%'
    """)
    sepp_docs = cursor.fetchone()
    print(f"SEPP documents: {sepp_docs['count']}")

    if sepp_docs['count'] > 0:
        cursor.execute("""
            SELECT document_name, document_type, id
            FROM documents
            WHERE document_name ILIKE '%SEPP%'
            LIMIT 5
        """)
        docs = cursor.fetchall()
        print("\nSample SEPP documents:")
        for doc in docs:
            print(f"  {doc['id']}: {doc['document_name']} ({doc['document_type']})")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
