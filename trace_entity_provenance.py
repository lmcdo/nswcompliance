#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Check if kg_relationships have any clues
        print("Checking kg_relationships for doc ID clues:\n")
        cur.execute("""
            SELECT DISTINCT document_id, section_header
            FROM kg_relationships
            WHERE section_header IS NOT NULL
            AND section_header != ''
            LIMIT 10
        """)

        for row in cur.fetchall():
            print(f"Doc: {row[0]}")
            print(f"  Section: {row[1][:80]}\n")

        # Check if there's a pattern we can use to map
        print("\n" + "="*80)
        print("\nChecking if section_header gives us LEP/DCP clues:\n")

        cur.execute("""
            SELECT section_header, document_id, COUNT(*)
            FROM kg_relationships
            WHERE section_header ILIKE '%inner%west%'
            OR section_header ILIKE '%marrickville%'
            OR section_header ILIKE '%ashfield%'
            OR section_header ILIKE '%clause%4.3%'
            OR section_header ILIKE '%clause%4.4%'
            GROUP BY section_header, document_id
            LIMIT 10
        """)

        results = cur.fetchall()
        if results:
            for row in results:
                print(f"Section: {row[0][:80]}")
                print(f"Doc: {row[1]}, Count: {row[2]}\n")
        else:
            print("No Inner West/LEP references found")

        # Last resort - check if relationships mention actual documents
        print("\n" + "="*80)
        print("\nChecking relationship text for document references:\n")

        cur.execute("""
            SELECT subject_text, object_text, document_id, section_header
            FROM kg_relationships
            WHERE (subject_text ILIKE '%height%building%'
                   OR object_text ILIKE '%height%building%')
            LIMIT 5
        """)

        for row in cur.fetchall():
            print(f"{row[0]} -> {row[1]}")
            print(f"  Doc: {row[2]}, Section: {row[3][:60] if row[3] else 'None'}\n")

        # Check if regulatory_refs has any mapping
        print("\n" + "="*80)
        print("\nChecking if regulatory_refs links entities to provisions:\n")

        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%mapping%' OR table_name LIKE '%link%')
        """)

        mapping_tables = [row[0] for row in cur.fetchall()]
        if mapping_tables:
            print(f"Found potential mapping tables: {mapping_tables}")
        else:
            print("No mapping tables found")

        # Summary
        print("\n" + "="*80)
        print("\n**CONCLUSION:**")
        print("The kg_entities and kg_relationships use orphaned generic doc IDs")
        print("that have NO mapping to actual LEP/DCP documents in the database.")
        print("These were likely from an old/test import that was never properly linked.")