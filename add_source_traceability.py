#!/usr/bin/env python3
"""
Add Source Traceability for Council Staff
=========================================
Add page numbers and document sections to regulatory_refs for professional users
"""

import sqlite3
import json
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate text similarity for matching"""
    return SequenceMatcher(None, a, b).ratio()

def add_source_traceability():
    """Add page numbers and section info to existing database entries"""
    
    print("ADDING SOURCE TRACEABILITY FOR COUNCIL STAFF")
    print("=" * 60)
    
    # Load RAG-Anything document flow data
    try:
        with open('multimodal_relationships_complete.json', 'r', encoding='utf-8') as f:
            flow_data = json.load(f)
        print(f"Loaded document flow data: {len(flow_data['documents'])} documents")
    except Exception as e:
        print(f"Error loading flow data: {e}")
        return 0
    
    # Connect to database and add new columns
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Add traceability columns if they don't exist
    try:
        cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN page_number INTEGER")
        cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN section_header TEXT")
        cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN document_position INTEGER")
        print("Added traceability columns to database")
    except sqlite3.OperationalError:
        print("Traceability columns already exist")
    
    # Get all current database entries
    cursor.execute("SELECT id, document_id, ref_type, ref_number, ref_context FROM regulatory_refs WHERE page_number IS NULL")
    db_entries = cursor.fetchall()
    print(f"Processing {len(db_entries)} database entries for traceability")
    
    matches_found = 0
    processed_docs = set()
    
    for entry_id, doc_id, ref_type, ref_number, ref_context in db_entries:
        
        # Find matching document in flow data
        doc_flow = None
        for flow_doc_name, flow_doc_data in flow_data['documents'].items():
            # Match document by name similarity
            if doc_id in flow_doc_name or flow_doc_name in doc_id or similarity(doc_id, flow_doc_name) > 0.7:
                doc_flow = flow_doc_data
                break
        
        if not doc_flow:
            continue
            
        # Process this document flow once
        if doc_id not in processed_docs:
            processed_docs.add(doc_id)
            print(f"  Processing: {doc_id[:60]}...")
        
        content_sequence = doc_flow.get('content_sequence', [])
        
        # Find best matching content item
        best_match = None
        best_score = 0.0
        
        search_text = f"{ref_number} {ref_context}".lower()[:200]
        
        current_section = "Introduction"
        
        for i, item in enumerate(content_sequence):
            item_text = item.get('text', '').lower()
            
            # Track current section header
            if item.get('text_level') == 1:
                current_section = item.get('text', '')[:50]
            
            # Calculate match score
            if item_text and len(item_text) > 10:
                score = similarity(search_text, item_text)
                
                # Boost score for exact matches of key terms
                if ref_number.lower() in item_text:
                    score += 0.3
                
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_match = {
                        'page': item.get('page_idx'),
                        'section': current_section,
                        'position': i,
                        'score': score
                    }
                    best_score = score
        
        # Update database if good match found
        if best_match and best_match['score'] > 0.4:
            cursor.execute("""
                UPDATE regulatory_refs 
                SET page_number = ?, section_header = ?, document_position = ?
                WHERE id = ?
            """, (
                best_match['page'],
                best_match['section'],
                best_match['position'],
                entry_id
            ))
            matches_found += 1
    
    # Commit changes
    conn.commit()
    
    # Check results
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL")
    entries_with_pages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    total_entries = cursor.fetchone()[0]
    
    # Sample results
    cursor.execute("""
        SELECT ref_type, ref_number, page_number, section_header 
        FROM regulatory_refs 
        WHERE page_number IS NOT NULL 
        LIMIT 5
    """)
    samples = cursor.fetchall()
    
    conn.close()
    
    print(f"\n" + "=" * 60)
    print("SOURCE TRACEABILITY INTEGRATION COMPLETE")
    print("=" * 60)
    print(f"Entries processed: {len(db_entries):,}")
    print(f"Matches found: {matches_found:,}")
    print(f"Coverage: {entries_with_pages}/{total_entries} entries ({entries_with_pages/total_entries*100:.1f}%)")
    print(f"Documents processed: {len(processed_docs)}")
    
    if samples:
        print(f"\nSample results:")
        for ref_type, ref_number, page_num, section in samples:
            print(f"  {ref_type}: '{ref_number}' → Page {page_num}, Section: {section}")
    
    return matches_found

def create_council_staff_query_demo():
    """Demo query showing traceability features for council staff"""
    
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    print("\nCOUNCIL STAFF TRACEABILITY DEMO")
    print("=" * 40)
    
    # Show entries with page numbers
    cursor.execute("""
        SELECT ref_type, ref_number, page_number, section_header, ref_context
        FROM regulatory_refs 
        WHERE page_number IS NOT NULL
        ORDER BY page_number
        LIMIT 5
    """)
    
    results = cursor.fetchall()
    
    print("Sample queries with source traceability:")
    for ref_type, ref_number, page_num, section, context in results:
        print(f"\nRule: {ref_number}")
        print(f"  Type: {ref_type}")
        print(f"  Source: Page {page_num}, {section}")
        print(f"  Context: {context[:80]}...")
    
    conn.close()

if __name__ == "__main__":
    matches = add_source_traceability()
    if matches > 0:
        print(f"\n✅ Successfully added traceability to {matches:,} entries")
        create_council_staff_query_demo()
    else:
        print(f"\n❌ No traceability matches found")