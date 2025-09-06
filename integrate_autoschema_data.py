#!/usr/bin/env python3
"""
Integrate AutoSchemaKG Data into Database
========================================
Add the 1,473 images + relationships from AutoSchemaKG to regulatory_refs table
"""

import json
import sqlite3

def integrate_autoschema_data():
    """Integrate AutoSchemaKG entities and relationships into database"""
    
    print("INTEGRATING AUTOSCHEMAKG DATA INTO DATABASE")
    print("=" * 60)
    
    # Load AutoSchemaKG data
    try:
        with open('autoschema_multimodal_complete.json', 'r', encoding='utf-8') as f:
            autoschema_data = json.load(f)
        print(f"Loaded AutoSchemaKG data with {len(autoschema_data.get('entities', []))} entities")
    except Exception as e:
        print(f"Error loading AutoSchemaKG data: {e}")
        return 0
    
    # Connect to database
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    initial_count = cursor.fetchone()[0]
    print(f"Initial database size: {initial_count:,} references")
    
    entries_added = 0
    
    try:
        # Process entities
        entities = autoschema_data.get('entities', [])
        print(f"\nProcessing {len(entities)} AutoSchemaKG entities...")
        
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            entity_id = entity.get('id', '')
            entity_name = entity.get('name', '')
            
            if entity_type == 'image':
                # Add image entities
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (
                    entity.get('document', 'unknown'),
                    'autoschema_image',
                    entity_id,
                    f"Image: {entity.get('path', '')} | Page: {entity.get('page', 0)} | Context: {entity.get('clause_context', 'none')}"
                ))
                entries_added += 1
                
            elif entity_type == 'document':
                # Add document metadata
                attributes = entity.get('attributes', {})
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (
                    entity_id,
                    'autoschema_document',
                    entity_name,
                    f"Images: {attributes.get('images', 0)} | Tables: {attributes.get('tables', 0)} | Sections: {attributes.get('text_sections', 0)}"
                ))
                entries_added += 1
                
            elif entity_type in ['clause', 'section', 'provision']:
                # Add regulatory clauses/sections
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (
                    entity.get('document', 'unknown'),
                    f'autoschema_{entity_type}',
                    entity.get('reference', entity_id),
                    entity.get('text', entity_name)[:500]
                ))
                entries_added += 1
        
        # Process relationships
        relationships = autoschema_data.get('relationships', [])
        print(f"Processing {len(relationships)} AutoSchemaKG relationships...")
        
        for rel in relationships:
            rel_type = rel.get('type', 'unknown')
            source = rel.get('source', '')
            target = rel.get('target', '')
            
            cursor.execute("""
                INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                VALUES (?, ?, ?, ?)
            """, (
                rel.get('document', 'unknown'),
                f'autoschema_relationship_{rel_type}',
                f"{source} -> {target}",
                rel.get('description', '')[:500]
            ))
            entries_added += 1
        
        # Process any visual-clause mappings
        if 'visual_mappings' in autoschema_data:
            mappings = autoschema_data['visual_mappings']
            print(f"Processing {len(mappings)} visual-clause mappings...")
            
            for mapping in mappings:
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (
                    mapping.get('document', 'unknown'),
                    'autoschema_visual_mapping',
                    mapping.get('clause', ''),
                    f"Image: {mapping.get('image_id', '')} | Description: {mapping.get('description', '')}"
                ))
                entries_added += 1
        
        # Commit changes
        conn.commit()
        
        # Check final state
        cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
        final_count = cursor.fetchone()[0]
        
        # Get breakdown of AutoSchemaKG entries
        cursor.execute("""
            SELECT ref_type, COUNT(*) 
            FROM regulatory_refs 
            WHERE ref_type LIKE 'autoschema_%' 
            GROUP BY ref_type 
            ORDER BY COUNT(*) DESC
        """)
        autoschema_breakdown = cursor.fetchall()
        
        conn.close()
        
        print(f"\n" + "=" * 60)
        print("AUTOSCHEMAKG INTEGRATION COMPLETE")
        print("=" * 60)
        print(f"Entries added: {entries_added:,}")
        print(f"Database size: {initial_count:,} → {final_count:,}")
        print(f"Growth: +{final_count - initial_count:,} references")
        
        if autoschema_breakdown:
            print(f"\nAutoSchemaKG entries by type:")
            for ref_type, count in autoschema_breakdown:
                print(f"  {ref_type}: {count:,}")
        
        return entries_added
        
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
        conn.close()
        return 0

if __name__ == "__main__":
    added = integrate_autoschema_data()
    if added > 0:
        print(f"\n✅ Successfully integrated {added:,} AutoSchemaKG entries")
    else:
        print(f"\n❌ AutoSchemaKG integration failed")