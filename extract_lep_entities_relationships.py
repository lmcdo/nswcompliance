#!/usr/bin/env python3
"""
Extract entities and relationships from Inner West LEP using AutoSchemaKG
Links entities back to regulatory_provisions for semantic search
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv('.env.local')

print("="*80)
print("LEP ENTITY/RELATIONSHIP EXTRACTION")
print("="*80)

# Check prerequisites
print("\n[1/6] Checking prerequisites...")

try:
    from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor
    from atlas_rag.kg_construction.triple_config import ProcessingConfig
    from atlas_rag.llm_generator import LLMGenerator
    from openai import OpenAI
    print("  ✓ AutoSchemaKG available")
except ImportError as e:
    print(f"  ✗ AutoSchemaKG not available: {e}")
    sys.exit(1)

api_key = os.getenv('OPENAI_API_KEY')
if not api_key or api_key == 'your_openai_api_key_here':
    print("  ✗ OpenAI API key not configured")
    print("  Set in .env.local: OPENAI_API_KEY=sk-...")
    sys.exit(1)
else:
    print(f"  ✓ OpenAI API key configured (ends with ...{api_key[-8:]})")

# Find LEP file
print("\n[2/6] Locating LEP file...")
lep_file = Path("docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation.pdf")

if not lep_file.exists():
    print(f"  ✗ LEP file not found: {lep_file}")
    sys.exit(1)

size_mb = lep_file.stat().st_size / 1_000_000
print(f"  ✓ Found: {lep_file.name}")
print(f"  Size: {size_mb:.1f} MB")

# Get document metadata from database
print("\n[3/6] Loading document metadata from database...")
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Get all LEP provision IDs for linking
        cur.execute("""
            SELECT id, ref_number, document_id, LEFT(provision_text, 100)
            FROM regulatory_provisions
            WHERE document_id LIKE '%Inner_West_Local_Environmental_Plan_2022%'
            ORDER BY id
            LIMIT 10
        """)

        provisions = cur.fetchall()
        print(f"  ✓ Found {len(provisions)} provisions in database (showing first 10)")
        for p in provisions[:3]:
            print(f"    - ID {p[0]}: Clause {p[1]} ({p[2]})")

# Get text from database (already extracted)
print("\n[4/6] Loading text from database...")
print("  Using pre-extracted full text from documents table...")

try:
    with get_safe_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT full_text
                FROM documents
                WHERE id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
            """)

            row = cur.fetchone()
            if not row:
                print("  ✗ Full text not found in database")
                sys.exit(1)

            full_text = row[0]
            print(f"  ✓ Loaded {len(full_text):,} characters from database")

except Exception as e:
    print(f"  ✗ Loading failed: {e}")
    sys.exit(1)

# Run AutoSchemaKG extraction
print("\n[5/6] Running AutoSchemaKG entity/relationship extraction...")
print("  This will use OpenAI API (estimated cost: $2-5)")
print("  Extracting entities and relationships from LEP text...")

try:
    import tempfile
    import shutil

    # Initialize LLM
    client = OpenAI(api_key=api_key)
    model_name = "gpt-4o-mini"
    triple_generator = LLMGenerator(client, model_name=model_name)

    # Create temp directory for chunks
    temp_dir = tempfile.mkdtemp(prefix='lep_extraction_')
    print(f"  Using temp directory: {temp_dir}")

    # Split text into chunks and write to files
    chunk_size = 2000
    chunks = []
    for i in range(0, len(full_text), chunk_size - 200):
        chunk = full_text[i:i + chunk_size]
        if chunk.strip() and len(chunk.strip()) > 100:
            # Only write first 10 chunks for testing
            if len(chunks) < 10:
                chunk_file = Path(temp_dir) / f"{len(chunks):04d}.txt"
                chunk_file.write_text(chunk, encoding='utf-8')
                chunks.append(chunk_file)
            else:
                break

    print(f"  Created {len(chunks)} text chunk files")
    print(f"  Files: {[f.name for f in chunks]}")

    # Configure extraction
    config = ProcessingConfig(
        model_path=model_name,
        data_directory=temp_dir,
        filename_pattern="*.txt",
        batch_size_triple=2,
        batch_size_concept=4,
        output_directory=f"{temp_dir}/output",
        max_new_tokens=1024,
        max_workers=1,
        remove_doc_spaces=False
    )

    # Initialize extractor
    extractor = KnowledgeGraphExtractor(
        model=triple_generator,
        config=config
    )

    print(f"  Running AutoSchemaKG extraction...")

    # Extract triples
    extracted_triples = extractor.run_extraction()

    entities = []
    relationships = []

    # Process extracted triples
    if extracted_triples:
        for triple in extracted_triples:
            if isinstance(triple, dict):
                subject = triple.get('subject', '')
                predicate = triple.get('predicate', '')
                obj = triple.get('object', '')

                if subject and obj:
                    relationships.append({
                        'subject': subject,
                        'predicate': predicate,
                        'object': obj
                    })

                    # Extract entities from subject and object
                    if subject not in [e['name'] for e in entities]:
                        entities.append({'name': subject, 'type': 'extracted'})
                    if obj not in [e['name'] for e in entities]:
                        entities.append({'name': obj, 'type': 'extracted'})

    print(f"\n  ✓ Extracted {len(entities)} entities and {len(relationships)} relationships")

    # Clean up temp directory
    shutil.rmtree(temp_dir, ignore_errors=True)

except Exception as e:
    print(f"  ✗ AutoSchemaKG extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Store in database
print("\n[6/6] Storing entities and relationships in database...")
print(f"  Inserting {len(entities)} entities...")
print(f"  Inserting {len(relationships)} relationships...")

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Clear old orphaned data
        print("  Clearing old orphaned entities/relationships...")
        cur.execute("DELETE FROM kg_relationships WHERE document_id LIKE 'nsw_planning_doc_%'")
        cur.execute("DELETE FROM kg_entities WHERE document_id LIKE 'nsw_planning_doc_%'")

        deleted_rels = cur.rowcount
        print(f"  ✓ Deleted {deleted_rels} orphaned relationships")

        # Insert entities
        doc_id = "Inner_West_Local_Environmental_Plan_2022___NSW_Legislation"
        timestamp = datetime.now().isoformat()

        for entity in entities:
            cur.execute("""
                INSERT INTO kg_entities (
                    entity_type, entity_name, document_id,
                    original_ref_type, extraction_timestamp
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                entity['type'],
                entity['name'],
                doc_id,
                'autoschemakg_lep_extraction',
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
                rel['subject'],
                rel['predicate'],
                rel['object'],
                doc_id,
                'autoschemakg_lep_extraction',
                timestamp
            ))

        conn.commit()
        print(f"  ✓ Inserted {len(entities)} entities")
        print(f"  ✓ Inserted {len(relationships)} relationships")

print("\n" + "="*80)
print("EXTRACTION COMPLETE")
print("="*80)
print(f"""
Successfully extracted and stored:
  - {len(entities)} entities
  - {len(relationships)} relationships
  - Linked to document: {doc_id}

Next steps:
  1. Run full extraction on all {len(chunks)} chunks (not just {len(test_chunks)})
  2. Link entities to regulatory_provisions IDs using text matching
  3. Test semantic search queries
""")