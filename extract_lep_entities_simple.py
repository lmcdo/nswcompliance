#!/usr/bin/env python3
"""
Extract entities and relationships from Inner West LEP using OpenAI directly
Simpler, faster, and more reliable than AutoSchemaKG wrapper
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv('.env.local')

print("="*80)
print("LEP ENTITY/RELATIONSHIP EXTRACTION (OpenAI Direct)")
print("="*80)

# Check API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key or api_key == 'your_openai_api_key_here':
    print("✗ OpenAI API key not configured")
    sys.exit(1)

client = OpenAI(api_key=api_key)
print(f"✓ OpenAI client initialized\n")

# Load LEP text from database
print("[1/4] Loading LEP text from database...")
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT full_text
            FROM documents
            WHERE id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
        """)

        full_text = cur.fetchone()[0]
        print(f"✓ Loaded {len(full_text):,} characters\n")

# Extract clause 4.3 and 4.4 sections for testing
print("[2/4] Extracting entities/relationships from Height and FSR clauses...")
print("  Using GPT-4 to extract structured knowledge...")

# Find clause 4.3
import re
match_43 = re.search(r'\n4\.3\n([^\n]+)\n(.*?)(?=\n4\.3[A-Z]|\n4\.4)', full_text, re.DOTALL)
match_44 = re.search(r'\n4\.4\n([^\n]+)\n(.*?)(?=\n4\.4[A-Z]|\n4\.5|\Z)', full_text, re.DOTALL)

clause_43_text = match_43.group(0) if match_43 else ""
clause_44_text = match_44.group(0) if match_44 else ""

test_text = clause_43_text + "\n\n" + clause_44_text

print(f"  Extracted {len(test_text)} chars from clauses 4.3 and 4.4")

# Extract entities and relationships
prompt = """Extract entities and relationships from this NSW planning legislation text.

For each entity, provide:
- name: the entity name
- type: the type (e.g., "planning_control", "measurement", "location", "objective")

For each relationship, provide:
- subject: entity 1
- predicate: relationship type
- object: entity 2

Return as JSON with two arrays: "entities" and "relationships".

Text:
"""

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert at extracting structured knowledge from legal documents."},
            {"role": "user", "content": prompt + test_text}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    result = json.loads(response.choices[0].message.content)
    entities = result.get('entities', [])
    relationships = result.get('relationships', [])

    print(f"✓ Extracted {len(entities)} entities and {len(relationships)} relationships\n")

except Exception as e:
    print(f"✗ Extraction failed: {e}")
    sys.exit(1)

# Store in database
print("[3/4] Storing in database...")

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Clear ALL old data (orphaned and LEP)
        cur.execute("TRUNCATE TABLE kg_relationships RESTART IDENTITY CASCADE")
        cur.execute("TRUNCATE TABLE kg_entities RESTART IDENTITY CASCADE")
        print("  Cleared all old entities/relationships")

        doc_id = "Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50"
        timestamp = datetime.now().isoformat()

        # Insert entities
        for entity in entities:
            cur.execute("""
                INSERT INTO kg_entities (
                    entity_type, entity_name, document_id,
                    original_ref_type, extraction_timestamp
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                entity.get('type', 'unknown'),
                entity.get('name', ''),
                doc_id,
                'openai_direct_extraction',
                timestamp
            ))

        # Insert relationships
        for rel in relationships:
            cur.execute("""
                INSERT INTO kg_relationships (
                    subject_text, predicate, object_text, document_id,
                    original_ref_type, extraction_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                rel.get('subject', ''),
                rel.get('predicate', ''),
                rel.get('object', ''),
                doc_id,
                'openai_direct_extraction',
                timestamp
            ))

        conn.commit()
        print(f"✓ Inserted {len(entities)} entities")
        print(f"✓ Inserted {len(relationships)} relationships\n")

# Verify
print("[4/4] Verification...")
with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM kg_entities
            WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan%'
        """)
        entity_count = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*) FROM kg_relationships
            WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan%'
        """)
        rel_count = cur.fetchone()[0]

        print(f"✓ Database contains {entity_count} entities and {rel_count} relationships")

        # Show sample
        print("\nSample entities:")
        cur.execute("""
            SELECT entity_name, entity_type
            FROM kg_entities
            WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan%'
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"  - {row[0]} ({row[1]})")

        print("\nSample relationships:")
        cur.execute("""
            SELECT subject_text, predicate, object_text
            FROM kg_relationships
            WHERE document_id LIKE 'Inner_West_Local_Environmental_Plan%'
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"  - {row[0]} --[{row[1]}]--> {row[2]}")

print("\n" + "="*80)
print("EXTRACTION COMPLETE")
print("="*80)
print(f"""
✓ Extracted from clauses 4.3 (Height) and 4.4 (FSR)
✓ Stored with proper document_id links
✓ Ready for semantic search

Cost: ~$0.10-0.20 (GPT-4o-mini)

Next: Run full extraction on all LEP clauses
""")