#!/usr/bin/env python3
"""
Import RAG-Anything entities and relationships to PostgreSQL database
This is the missing piece - we have the semantic data but it's not in the database!
"""
import os
import json
import psycopg2
from datetime import datetime
from pathlib import Path

def connect_to_database():
 """Connect to PostgreSQL database"""
 try:
 conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning",
 user="postgres",
 password="postgres"
 )
 return conn
 except Exception as e:
 print(f"ERROR: Database connection failed: {e}")
 return None

def create_rag_tables(conn):
 """Create tables for RAG-Anything entities and relationships"""
 
 cursor = conn.cursor()
 
 # Create RAG entities table
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS rag_entities (
 id SERIAL PRIMARY KEY,
 document_id TEXT,
 entity_name TEXT NOT NULL,
 entity_type TEXT DEFAULT 'planning_entity',
 extraction_method TEXT DEFAULT 'rag_anything',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(document_id, entity_name)
 );
 """)
 
 # Create RAG relationships table 
 cursor.execute("""
 CREATE TABLE IF NOT EXISTS rag_relationships (
 id SERIAL PRIMARY KEY,
 document_id TEXT,
 source_entity TEXT NOT NULL,
 target_entity TEXT NOT NULL,
 relationship_type TEXT DEFAULT 'planning_relation',
 extraction_method TEXT DEFAULT 'rag_anything',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(document_id, source_entity, target_entity)
 );
 """)
 
 # Create indexes for performance
 cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_entities_name ON rag_entities(entity_name);")
 cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_entities_doc ON rag_entities(document_id);")
 cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_relationships_source ON rag_relationships(source_entity);")
 cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_relationships_target ON rag_relationships(target_entity);")
 
 conn.commit()
 print("SUCCESS: RAG tables created successfully")

def load_rag_data():
 """Load RAG-Anything data from storage files"""
 
 rag_dirs = ['rag_storage', 'rag_fixed_storage']
 
 for rag_dir in rag_dirs:
 if Path(rag_dir).exists():
 print(f"Loading RAG data from {rag_dir}/")
 
 # Load entities
 entities_file = Path(rag_dir) / "kv_store_full_entities.json"
 relationships_file = Path(rag_dir) / "kv_store_full_relations.json"
 
 entities_data = {}
 relationships_data = {}
 
 if entities_file.exists():
 with open(entities_file, 'r', encoding='utf-8') as f:
 entities_data = json.load(f)
 print(f" Loaded entities from {entities_file}")
 
 if relationships_file.exists():
 with open(relationships_file, 'r', encoding='utf-8') as f:
 relationships_data = json.load(f)
 print(f" Loaded relationships from {relationships_file}")
 
 return entities_data, relationships_data, rag_dir
 
 print("ERROR: No RAG data found in storage directories")
 return {}, {}, None

def import_entities(conn, entities_data, rag_dir):
 """Import RAG entities to database"""
 
 cursor = conn.cursor()
 entities_imported = 0
 
 print(f"Importing entities from {rag_dir}...")
 
 for doc_id, doc_data in entities_data.items():
 entity_names = doc_data.get('entity_names', [])
 
 for entity_name in entity_names:
 if not entity_name.strip():
 continue
 
 try:
 cursor.execute("""
 INSERT INTO rag_entities (document_id, entity_name, entity_type, extraction_method)
 VALUES (%s, %s, %s, %s)
 ON CONFLICT (document_id, entity_name) DO NOTHING
 """, (doc_id, entity_name.strip(), 'planning_entity', f'rag_anything_{rag_dir}'))
 
 entities_imported += 1
 
 except Exception as e:
 print(f" Error importing entity '{entity_name}': {e}")
 continue
 
 conn.commit()
 print(f"SUCCESS: Imported {entities_imported} entities")
 return entities_imported

def import_relationships(conn, relationships_data, rag_dir):
 """Import RAG relationships to database"""
 
 cursor = conn.cursor()
 relationships_imported = 0
 
 print(f"Importing relationships from {rag_dir}...")
 
 for doc_id, doc_data in relationships_data.items():
 relation_pairs = doc_data.get('relation_pairs', [])
 
 for pair in relation_pairs:
 if len(pair) != 2:
 continue
 
 source_entity, target_entity = pair[0].strip(), pair[1].strip()
 
 if not source_entity or not target_entity:
 continue
 
 try:
 cursor.execute("""
 INSERT INTO rag_relationships (document_id, source_entity, target_entity, relationship_type, extraction_method)
 VALUES (%s, %s, %s, %s, %s)
 ON CONFLICT (document_id, source_entity, target_entity) DO NOTHING
 """, (doc_id, source_entity, target_entity, 'planning_relation', f'rag_anything_{rag_dir}'))
 
 relationships_imported += 1
 
 except Exception as e:
 print(f" Error importing relationship '{source_entity}' -> '{target_entity}': {e}")
 continue
 
 conn.commit()
 print(f"SUCCESS: Imported {relationships_imported} relationships")
 return relationships_imported

def verify_import(conn):
 """Verify the imported data"""
 
 cursor = conn.cursor()
 
 # Count entities
 cursor.execute("SELECT COUNT(*) FROM rag_entities;")
 entity_count = cursor.fetchone()[0]
 
 # Count relationships
 cursor.execute("SELECT COUNT(*) FROM rag_relationships;")
 relationship_count = cursor.fetchone()[0]
 
 # Sample entities
 cursor.execute("SELECT entity_name FROM rag_entities WHERE entity_name ILIKE '%zone%' OR entity_name ILIKE '%setback%' OR entity_name ILIKE '%fsr%' LIMIT 5;")
 sample_entities = [row[0] for row in cursor.fetchall()]
 
 # Sample relationships
 cursor.execute("SELECT source_entity, target_entity FROM rag_relationships LIMIT 5;")
 sample_relationships = cursor.fetchall()
 
 print(f"\nVERIFICATION RESULTS:")
 print(f" Total entities: {entity_count}")
 print(f" Total relationships: {relationship_count}")
 print(f" Sample planning entities: {sample_entities}")
 print(f" Sample relationships: {sample_relationships[:3]}")
 
 return entity_count, relationship_count

def create_marker():
 """Create completion marker"""
 Path("migration_markers").mkdir(exist_ok=True)
 with open("migration_markers/rag_anything_import_completed.marker", 'w') as f:
 f.write(f"RAG-Anything import completed: {datetime.now().isoformat()}\n")
 print("SUCCESS: Created completion marker")

def main():
 """Main import process"""
 
 print("RAG-ANYTHING DATABASE IMPORT")
 print("=" * 50)
 print("Importing semantic entities and relationships to PostgreSQL")
 
 # Step 1: Connect to database
 conn = connect_to_database()
 if not conn:
 print("ERROR: Cannot connect to database")
 return False
 
 # Step 2: Create tables
 create_rag_tables(conn)
 
 # Step 3: Load RAG data
 entities_data, relationships_data, rag_dir = load_rag_data()
 if not entities_data and not relationships_data:
 print("ERROR: No RAG data to import")
 return False
 
 # Step 4: Import entities
 entities_imported = import_entities(conn, entities_data, rag_dir)
 
 # Step 5: Import relationships
 relationships_imported = import_relationships(conn, relationships_data, rag_dir)
 
 # Step 6: Verify import
 entity_count, relationship_count = verify_import(conn)
 
 # Step 7: Create marker
 create_marker()
 
 conn.close()
 
 print(f"\n" + "=" * 50)
 print("RAG-ANYTHING IMPORT COMPLETED SUCCESSFULLY")
 print(f" Entities imported: {entities_imported}")
 print(f" Relationships imported: {relationships_imported}")
 print(f" Total in database: {entity_count} entities, {relationship_count} relationships")
 print(f"Now the database has the semantic planning data!")
 print("=" * 50)
 
 return True

if __name__ == "__main__":
 success = main()
 exit(0 if success else 1)