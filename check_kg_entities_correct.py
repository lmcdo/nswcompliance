#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Search for LEP-related entities
        print("Searching for LEP/height/FSR entities:")
        cur.execute("""
            SELECT id, entity_name, entity_type, document_id, original_ref_type, original_ref_id
            FROM kg_entities
            WHERE entity_name ILIKE '%height%'
            OR entity_name ILIKE '%floor space%'
            OR entity_name ILIKE '%building%height%'
            OR entity_description ILIKE '%clause 4.3%'
            OR entity_description ILIKE '%clause 4.4%'
            LIMIT 20
        """)

        results = cur.fetchall()
        if results:
            print(f"Found {len(results)} entities:\n")
            for row in results:
                print(f"ID: {row[0]}")
                print(f"Name: {row[1]}")
                print(f"Type: {row[2]}")
                print(f"Doc: {row[3]}")
                print(f"Ref type: {row[4]}, Ref ID: {row[5]}")
                print("="*80 + "\n")
        else:
            print("No LEP-related entities found")

        # Check total and sample
        print("\n" + "="*80)
        cur.execute("SELECT COUNT(*) FROM kg_entities")
        total = cur.fetchone()[0]
        print(f"Total entities: {total}")

        print("\nSample entities:")
        cur.execute("""
            SELECT entity_name, entity_type, document_id, original_ref_type, original_ref_id
            FROM kg_entities
            ORDER BY id
            LIMIT 10
        """)
        for row in cur.fetchall():
            print(f"\n  Name: {row[0][:80]}")
            print(f"  Type: {row[1]}, Doc: {row[2]}")
            if row[3] and row[4]:
                print(f"  Links to: {row[3]} ID={row[4]}")

        # Check if any link to regulatory_provisions
        print("\n" + "="*80)
        print("\nEntities linking to regulatory_provisions:")
        cur.execute("""
            SELECT COUNT(*)
            FROM kg_entities
            WHERE original_ref_type = 'regulatory_provision'
        """)
        count = cur.fetchone()[0]
        print(f"  {count} entities")

        if count > 0:
            cur.execute("""
                SELECT e.entity_name, e.original_ref_id, p.ref_number, p.document_id
                FROM kg_entities e
                JOIN regulatory_provisions p ON e.original_ref_id::int = p.id
                WHERE e.original_ref_type = 'regulatory_provision'
                AND p.document_id LIKE '%Local_Environmental_Plan%'
                LIMIT 10
            """)
            for row in cur.fetchall():
                print(f"\n  Entity: {row[0][:60]}")
                print(f"  Links to: {row[3]} clause {row[2]}")