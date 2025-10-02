#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check what distinct document_ids are in kg_entities
        print("Document IDs in kg_entities:\n")
        cur.execute("""
            SELECT DISTINCT document_id, COUNT(*)
            FROM kg_entities
            GROUP BY document_id
            ORDER BY document_id
            LIMIT 30
        """)

        kg_docs = []
        for row in cur.fetchall():
            kg_docs.append(row[0])
            print(f"{row[0]}: {row[1]} entities")

        # Check if ANY of these exist in documents table
        print("\n" + "="*80)
        print("\nChecking if these doc_ids exist in documents table:\n")

        if kg_docs:
            placeholders = ','.join(['%s'] * len(kg_docs[:10]))
            cur.execute(f"""
                SELECT id, pdf_name, document_type
                FROM documents
                WHERE id IN ({placeholders})
            """, kg_docs[:10])

            results = cur.fetchall()
            if results:
                print(f"Found {len(results)} matching documents:")
                for row in results:
                    print(f"  {row[0]}: {row[2]} - {row[1][:60]}")
            else:
                print("NONE of the kg_entities document_ids exist in documents table!")

        # Let's look at what kg_entities actually has as metadata
        print("\n" + "="*80)
        print("\nSample entity with full metadata:\n")
        cur.execute("""
            SELECT *
            FROM kg_entities
            WHERE entity_name ILIKE '%height%'
            LIMIT 1
        """)

        row = cur.fetchone()
        if row:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'kg_entities'
                ORDER BY ordinal_position
            """)
            columns = [c[0] for c in cur.fetchall()]

            for i, col in enumerate(columns):
                if row[i]:
                    print(f"{col}: {row[i]}")

        # Check if there's a mapping in another table
        print("\n" + "="*80)
        print("\nChecking if generic doc IDs map via section_header or other metadata:\n")

        cur.execute("""
            SELECT DISTINCT section_header
            FROM kg_entities
            WHERE section_header IS NOT NULL
            AND section_header != ''
            LIMIT 10
        """)

        for row in cur.fetchall():
            print(f"  Section: {row[0][:80]}")