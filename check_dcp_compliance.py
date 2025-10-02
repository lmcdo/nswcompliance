#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== DCP COMPLIANCE DATA ===")

    # Check for specific compliance-related DCP provisions
    compliance_terms = [
        'building height', 'floor space ratio', 'setback', 'privacy', 
        'landscaping', 'parking', 'site coverage', 'heritage'
    ]

    for term in compliance_terms:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM regulatory_provisions
            WHERE provision_text ILIKE %s
            AND document_id ILIKE '%inner%west%'
            AND document_id ILIKE '%dcp%'
        """, (f'%{term}%',))
        
        count = cursor.fetchone()['count']
        print(f"{term.title()}: {count} provisions")

    print("\n=== SAMPLE COMPLIANCE PROVISIONS ===")

    # Get specific examples for building height
    cursor.execute("""
        SELECT ref_number, section_header, provision_text, document_id
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%building height%'
        AND document_id ILIKE '%inner%west%'
        AND document_id ILIKE '%dcp%'
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 50
        LIMIT 3
    """)
    
    height_provisions = cursor.fetchall()
    print("Building Height provisions:")
    for prov in height_provisions:
        text = prov['provision_text'][:300] + '...' if len(prov['provision_text']) > 300 else prov['provision_text']
        print(f"  {prov['ref_number']}: {prov['section_header']}")
        print(f"    Doc: {prov['document_id']}")
        print(f"    Content: {text}")
        print()

    # Check what document types we have for Inner West
    cursor.execute("""
        SELECT DISTINCT document_id, COUNT(*) as provision_count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%'
        AND document_id ILIKE '%dcp%'
        GROUP BY document_id
        ORDER BY provision_count DESC
        LIMIT 10
    """)
    
    doc_counts = cursor.fetchall()
    print("Inner West DCP documents by provision count:")
    for doc in doc_counts:
        print(f"  {doc['document_id']}: {doc['provision_count']} provisions")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
