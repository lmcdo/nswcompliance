#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check kg_entities table structure
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'kg_entities'
            ORDER BY ordinal_position
        """)

        print("kg_entities columns:")
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")

        # Check if LEP/DCP entities exist
        print("\n" + "="*80)
        print("\nSearching for LEP entities:")
        cur.execute("""
            SELECT entity_id, entity_text, entity_type, document_id
            FROM kg_entities
            WHERE entity_text ILIKE '%height%buildings%'
            OR entity_text ILIKE '%floor space ratio%'
            OR entity_text ILIKE '%LEP%'
            LIMIT 10
        """)

        results = cur.fetchall()
        if results:
            for row in results:
                print(f"\nEntity ID: {row[0]}")
                print(f"Text: {row[1]}")
                print(f"Type: {row[2]}")
                print(f"Doc: {row[3]}")
        else:
            print("No matches for LEP-related entities")

        # Check total count and sample
        print("\n" + "="*80)
        cur.execute("SELECT COUNT(*) FROM kg_entities")
        total = cur.fetchone()[0]
        print(f"\nTotal entities: {total}")

        print("\nSample entities:")
        cur.execute("""
            SELECT entity_id, entity_text, entity_type, document_id
            FROM kg_entities
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"\n  {row[1][:80]} (Type: {row[2]}, Doc: {row[3]})")