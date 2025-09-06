#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime

def import_autoschemakg_relationships():
    print("IMPORTING AUTOSCHEMAKG RELATIONSHIPS")
    print("=" * 50)
    
    # Load AutoSchemaKG data
    print("Loading AutoSchemaKG extraction file...")
    with open('autoschemakg_output_ollama_final/kg_extraction/llama3.1_8b_nsw_planning_docs_output_20250829000809_1_in_1.json', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    documents = []
    for line in lines:
        if line.strip():
            try:
                documents.append(json.loads(line))
            except:
                continue
    
    print(f"Loaded {len(documents)} documents with relationships")
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Create entity mapping
    entity_id_map = {}
    entities_imported = 0
    
    # Import entities first
    print("Importing entities...")
    
    for doc in documents:
        doc_id = doc.get('id', '')
        
        # Extract unique entities from relationships
        for rel in doc.get('entity_relation_dict', []):
            head = rel.get('Head', '').strip()
            tail = rel.get('Tail', '').strip()
            
            # Create entities if not exists
            for entity_name in [head, tail]:
                if entity_name and entity_name not in entity_id_map:
                    cursor.execute('''
                        INSERT INTO kg_entities 
                        (entity_type, entity_name, document_id, original_ref_type, extraction_timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', ('autoschemakg_entity', entity_name, doc_id, 'autoschemakg_import', datetime.now().isoformat()))
                    
                    entity_id_map[entity_name] = cursor.lastrowid
                    entities_imported += 1
    
    print(f"Imported {entities_imported} unique entities")
    
    # Import relationships
    print("Importing relationships...")
    relationships_imported = 0
    
    for doc in documents:
        doc_id = doc.get('id', '')
        
        # Import entity-to-entity relationships
        for rel in doc.get('entity_relation_dict', []):
            head = rel.get('Head', '').strip()
            relation = rel.get('Relation', '').strip()
            tail = rel.get('Tail', '').strip()
            
            if head and tail and relation:
                subject_entity_id = entity_id_map.get(head)
                object_entity_id = entity_id_map.get(tail)
                
                if subject_entity_id and object_entity_id:
                    cursor.execute('''
                        INSERT INTO kg_relationships 
                        (subject_text, predicate, object_text, subject_entity_id, 
                         object_entity_id, document_id, original_ref_type, 
                         extraction_timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (head, relation, tail, subject_entity_id, object_entity_id,
                          doc_id, 'autoschemakg_entity_relation', datetime.now().isoformat()))
                    relationships_imported += 1
        
        # Import event relationships for temporal/causal analysis
        for rel in doc.get('event_relation_dict', []):
            head = rel.get('Head', '').strip()
            relation = rel.get('Relation', '').strip() 
            tail = rel.get('Tail', '').strip()
            
            if head and tail and relation:
                cursor.execute('''
                    INSERT INTO kg_relationships
                    (subject_text, predicate, object_text, document_id, 
                     original_ref_type, extraction_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (head, relation, tail, doc_id, 
                      'autoschemakg_event_relation', datetime.now().isoformat()))
                relationships_imported += 1
    
    conn.commit()
    
    # Verification
    cursor.execute("SELECT COUNT(*) FROM kg_entities")
    final_entities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM kg_relationships")
    final_relationships = cursor.fetchone()[0]
    
    print(f"\nIMPORT COMPLETED:")
    print(f"  Entities in kg_entities: {final_entities:,}")
    print(f"  Relationships in kg_relationships: {final_relationships:,}")
    
    conn.close()
    
    # Create completion marker
    with open('migration_markers/autoschemakg_import_completed.marker', 'w') as f:
        f.write(f"AutoSchemaKG import completed: {datetime.now().isoformat()}\n")
        f.write(f"Entities imported: {final_entities}\n")
        f.write(f"Relationships imported: {final_relationships}\n")
        f.write("Status: SUCCESS\n")
    
    return final_entities, final_relationships

if __name__ == "__main__":
    entities, relationships = import_autoschemakg_relationships()
    
    if relationships >= 4000:
        print("✅ AUTOSCHEMAKG IMPORT SUCCESSFUL")
        exit(0)
    else:
        print("❌ AUTOSCHEMAKG IMPORT FAILED - INSUFFICIENT DATA")
        exit(1)
