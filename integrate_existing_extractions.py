#!/usr/bin/env python3
"""
Integrate Existing LangExtract Results
=====================================
Merge existing extraction results from previous runs into the database
while the ultimate pipeline processes remaining documents.
"""

import json
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def integrate_existing_extractions():
    """Integrate all existing LangExtract results into database"""
    
    print("INTEGRATING EXISTING LANGEXTRACT RESULTS")
    print("=" * 60)
    
    # Find all existing extraction files
    extraction_files = []
    
    # Recent comprehensive extractions
    recent_dir = Path("monitored_pipeline_output")
    if recent_dir.exists():
        for file in recent_dir.glob("*_results.json"):
            extraction_files.append(file)
    
    # Older LangExtract results
    old_dir = Path("langextract_verified_output")
    if old_dir.exists():
        for file in old_dir.glob("*_verified.json"):
            extraction_files.append(file)
    
    print(f"Found {len(extraction_files)} existing extraction files")
    
    if not extraction_files:
        print("No existing extractions found")
        return
    
    # Connect to database
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Track integration stats
    stats = {
        'files_processed': 0,
        'total_entries_added': 0,
        'entities_added': 0,
        'relationships_added': 0,
        'provisions_added': 0,
        'errors': []
    }
    
    for file_path in extraction_files:
        try:
            print(f"Processing: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract document info
            doc_id = data.get('document_id') or data.get('document', {}).get('id', file_path.stem)
            doc_name = data.get('document_name') or data.get('document', {}).get('name', file_path.stem)
            
            # Get extraction results (different formats)
            extraction_results = data.get('extraction_results', {})
            if not extraction_results:
                # Try older format
                extraction_results = {
                    'entities': data.get('verified_provisions', []),
                    'relationships': data.get('relationships', []),
                    'provisions': data.get('provisions', [])
                }
            
            entries_added = populate_database_from_extraction(cursor, doc_id, extraction_results)
            
            stats['files_processed'] += 1
            stats['total_entries_added'] += entries_added
            
            # Count by type
            stats['entities_added'] += len(extraction_results.get('entities', []))
            stats['relationships_added'] += len(extraction_results.get('relationships', []))  
            stats['provisions_added'] += len(extraction_results.get('provisions', []))
            
            print(f"  Added {entries_added} database entries")
            
        except Exception as e:
            error_msg = f"Error processing {file_path.name}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"  ERROR: {str(e)}")
            continue
    
    # Commit all changes
    conn.commit()
    
    # Check final database state
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    total_refs = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT ref_type, COUNT(*) 
        FROM regulatory_refs 
        GROUP BY ref_type 
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    ref_breakdown = cursor.fetchall()
    
    conn.close()
    
    # Print integration summary
    print("\n" + "=" * 60)
    print("INTEGRATION COMPLETE")
    print("=" * 60)
    print(f"Files processed: {stats['files_processed']}")
    print(f"Database entries added: {stats['total_entries_added']:,}")
    print(f"Entities integrated: {stats['entities_added']:,}")
    print(f"Relationships integrated: {stats['relationships_added']:,}")
    print(f"Provisions integrated: {stats['provisions_added']:,}")
    print(f"Errors: {len(stats['errors'])}")
    print(f"\nTotal regulatory_refs in database: {total_refs:,}")
    
    if ref_breakdown:
        print(f"\nTop reference types:")
        for ref_type, count in ref_breakdown:
            print(f"  {ref_type}: {count:,}")
    
    if stats['errors']:
        print(f"\nErrors encountered:")
        for error in stats['errors'][:5]:
            print(f"  - {error}")
    
    return stats

def populate_database_from_extraction(cursor, doc_id, extraction_results):
    """Populate database with extraction results"""
    entries_added = 0
    
    try:
        # Add entities (various formats)
        entities = extraction_results.get('entities', [])
        for entity in entities:
            if isinstance(entity, dict):
                ref_type = entity.get('type', 'entity')
                ref_number = entity.get('reference') or entity.get('clause_reference', '')
                ref_context = entity.get('text', '')[:500]
                
                if ref_number:
                    cursor.execute("""
                        INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, f"entity_{ref_type}", ref_number, ref_context))
                    entries_added += 1
        
        # Add relationships
        relationships = extraction_results.get('relationships', [])
        for rel in relationships:
            if isinstance(rel, dict) and rel.get('source') and rel.get('target'):
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, f"relationship_{rel.get('type', 'unknown')}", 
                      f"{rel.get('source')} -> {rel.get('target')}", 
                      rel.get('evidence', '')[:500]))
                entries_added += 1
        
        # Add provisions  
        provisions = extraction_results.get('provisions', [])
        for prov in provisions:
            if isinstance(prov, dict):
                entity = prov.get('entity') or prov.get('clause_reference', '')
                if entity:
                    cursor.execute("""
                        INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                        VALUES (?, ?, ?, ?)
                    """, (doc_id, f"provision_{prov.get('type', 'unknown')}", 
                          entity, prov.get('text', '')[:500]))
                    entries_added += 1
        
        # Add formal entities (newer format)
        formal_entities = extraction_results.get('formal_entities', [])
        for entity in formal_entities:
            if isinstance(entity, dict) and entity.get('reference'):
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, f"formal_{entity.get('category', entity.get('type', 'entity'))}", 
                      entity.get('reference'), entity.get('text', '')[:500]))
                entries_added += 1
        
        # Add contextual information (newer format)
        contextual = extraction_results.get('contextual_information', [])
        for context in contextual:
            if isinstance(context, dict):
                cursor.execute("""
                    INSERT OR IGNORE INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, f"context_{context.get('type', 'info')}", 
                      context.get('applies_to', 'general'), context.get('text', '')[:500]))
                entries_added += 1
        
    except Exception as e:
        print(f"    Database error: {e}")
        
    return entries_added

if __name__ == "__main__":
    stats = integrate_existing_extractions()
    if stats and stats['files_processed'] > 0:
        print(f"\n[SUCCESS] Integrated {stats['files_processed']} extraction files")
    else:
        print("\n[WARNING] No extractions integrated")