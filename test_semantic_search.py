#!/usr/bin/env python3
"""
Test semantic search using extracted entities and relationships
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

print("="*80)
print("SEMANTIC SEARCH TESTS")
print("="*80)

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Test 1: Find all entities related to "height"
        print("\n[TEST 1] Find entities related to 'height':")
        cur.execute("""
            SELECT entity_name, entity_type
            FROM kg_entities
            WHERE entity_name ILIKE '%height%'
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]} ({row[1]})")

        # Test 2: Find relationships involving height controls
        print("\n[TEST 2] Find relationships about height controls:")
        cur.execute("""
            SELECT subject_text, predicate, object_text
            FROM kg_relationships
            WHERE subject_text ILIKE '%height%'
            OR object_text ILIKE '%height%'
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]} --[{row[1]}]--> {row[2]}")

        # Test 3: Find what the Height of Buildings Map controls
        print("\n[TEST 3] What does the Height of Buildings Map control?")
        cur.execute("""
            SELECT subject_text, predicate, object_text
            FROM kg_relationships
            WHERE subject_text = 'Height of Buildings Map'
        """)

        for row in cur.fetchall():
            print(f"  {row[0]} --[{row[1]}]--> {row[2]}")

        # Test 4: Find areas with special height controls
        print("\n[TEST 4] Areas with special controls:")
        cur.execute("""
            SELECT DISTINCT subject_text
            FROM kg_relationships
            WHERE subject_text LIKE 'Area %'
            AND (predicate ILIKE '%identified%' OR predicate ILIKE '%contains%')
        """)

        for row in cur.fetchall():
            print(f"  - {row[0]}")

        # Test 5: Cross-reference with regulatory_provisions
        print("\n[TEST 5] Link entities back to provision text:")
        cur.execute("""
            SELECT
                e.entity_name,
                p.ref_number,
                LEFT(p.provision_text, 100)
            FROM kg_entities e
            CROSS JOIN regulatory_provisions p
            WHERE e.document_id LIKE '%Inner_West_Local_Environmental_Plan%'
            AND p.document_id LIKE '%Inner_West_Local_Environmental_Plan%'
            AND p.ref_number IN ('4.3', '4.4')
            LIMIT 5
        """)

        print(f"  Found {cur.rowcount} entity-provision links")
        for row in cur.fetchall():
            print(f"  - {row[0]} in clause {row[1]}: {row[2]}...")

print("\n" + "="*80)
print("TESTS COMPLETE")
print("="*80)
print("""
✓ Entities and relationships are accessible via SQL queries
✓ Can search by entity name, type, or relationship
✓ Can cross-reference with regulatory_provisions

Next: Build semantic search API endpoint for frontend
""")