#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check what the generic doc IDs actually are
        cur.execute("""
            SELECT id, pdf_name, document_type
            FROM documents
            WHERE id LIKE 'nsw_planning_doc_%'
            ORDER BY id
            LIMIT 10
        """)

        results = cur.fetchall()
        print(f"Generic document IDs:\n")

        for row in results:
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Type: {row[2]}")
            print()

        # Check if these have relationships
        print("\n" + "="*80)
        print("Checking relationships for first doc:")
        cur.execute("""
            SELECT subject_text, predicate, object_text, section_header
            FROM kg_relationships
            WHERE document_id = 'nsw_planning_doc_000'
            LIMIT 5
        """)

        for row in cur.fetchall():
            print(f"\n{row[0]} --[{row[1]}]--> {row[2]}")
            if row[3]:
                print(f"  Section: {row[3]}")