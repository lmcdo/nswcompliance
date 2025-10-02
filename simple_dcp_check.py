#!/usr/bin/env python3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

try:
    conn = get_dict_connection()
    cursor = conn.cursor()

    print("=== INNER WEST DCP CONTENT ===")

    # Check for building height provisions
    cursor.execute("""
        SELECT ref_number, section_header, provision_text, document_id
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%building height%'
        AND document_id ILIKE '%inner%west%'
        LIMIT 5
    """)
    
    height_provisions = cursor.fetchall()
    print(f"Building height provisions: {len(height_provisions)}")
    for prov in height_provisions:
        if prov['provision_text']:
            text = prov['provision_text'][:200] + '...' if len(prov['provision_text']) > 200 else prov['provision_text']
            print(f"  {prov['ref_number']}: {text}")

    print(f"\n=== ACTUAL CLAUSE CONTENT SAMPLE ===")
    
    # Get provisions with substantial content
    cursor.execute("""
        SELECT ref_number, section_header, provision_text, document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%'
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 100
        LIMIT 5
    """)
    
    content_provisions = cursor.fetchall()
    for prov in content_provisions:
        print(f"Ref: {prov['ref_number']}")
        print(f"Doc: {prov['document_id']}")
        print(f"Content: {prov['provision_text'][:300]}...")
        print()

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
