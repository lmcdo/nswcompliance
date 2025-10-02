#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Map the generic doc IDs to actual documents
        print("Mapping generic doc IDs to actual documents:\n")

        # Get documents that match the pattern
        cur.execute("""
            SELECT id, pdf_name, document_type, word_count
            FROM documents
            WHERE id LIKE 'nsw_planning_doc_%'
            ORDER BY id
            LIMIT 30
        """)

        doc_map = {}
        for row in cur.fetchall():
            doc_map[row[0]] = {
                'name': row[1],
                'type': row[2],
                'words': row[3]
            }
            print(f"{row[0]}: {row[2]} - {row[1][:80]}")

        # Now check which have entities
        print("\n" + "="*80)
        print("\nChecking which docs have height/FSR entities:\n")

        cur.execute("""
            SELECT document_id, COUNT(*)
            FROM kg_entities
            WHERE entity_name ILIKE '%height%'
            OR entity_name ILIKE '%floor space%'
            OR entity_name ILIKE '%FSR%'
            GROUP BY document_id
            ORDER BY COUNT(*) DESC
            LIMIT 15
        """)

        for row in cur.fetchall():
            doc_id = row[0]
            count = row[1]
            if doc_id in doc_map:
                info = doc_map[doc_id]
                print(f"{doc_id}: {count} entities")
                print(f"  -> {info['type']}: {info['name'][:70]}")
                print()
            else:
                print(f"{doc_id}: {count} entities (doc info not found)")

        # Check for LEP specifically
        print("\n" + "="*80)
        print("\nLEP documents with entities:\n")
        cur.execute("""
            SELECT d.id, d.pdf_name, COUNT(e.id)
            FROM documents d
            LEFT JOIN kg_entities e ON d.id = e.document_id
            WHERE d.document_type = 'LEP'
            AND d.id LIKE 'nsw_planning_doc_%'
            GROUP BY d.id, d.pdf_name
            HAVING COUNT(e.id) > 0
            LIMIT 10
        """)

        results = cur.fetchall()
        if results:
            for row in results:
                print(f"{row[0]}: {row[2]} entities")
                print(f"  {row[1]}")
        else:
            print("NO LEP documents found with entities using generic IDs")