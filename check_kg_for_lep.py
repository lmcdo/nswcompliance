#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check if generic doc IDs map to actual LEP documents
        cur.execute("""
            SELECT r.document_id, d.pdf_name, d.document_type, COUNT(*)
            FROM kg_relationships r
            JOIN documents d ON r.document_id = d.id
            WHERE d.document_type = 'LEP'
            GROUP BY r.document_id, d.pdf_name, d.document_type
            LIMIT 10
        """)

        results = cur.fetchall()
        print(f"Knowledge graph relationships for LEP documents:\n")

        if results:
            for row in results:
                print(f"KG Doc ID: {row[0]}")
                print(f"Actual document: {row[1]}")
                print(f"Type: {row[2]}")
                print(f"Relationships: {row[3]}")
                print("=" * 80 + "\n")
        else:
            print("NO relationships found for LEP documents")

            # Check what documents DO have relationships
            print("\nDocuments WITH relationships:")
            cur.execute("""
                SELECT d.id, d.pdf_name, d.document_type, COUNT(r.id)
                FROM documents d
                LEFT JOIN kg_relationships r ON d.id = r.document_id
                WHERE r.id IS NOT NULL
                GROUP BY d.id, d.pdf_name, d.document_type
                LIMIT 10
            """)
            for row in cur.fetchall():
                print(f"{row[2]}: {row[1]} ({row[3]} relationships)")