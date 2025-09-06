#!/usr/bin/env python3
"""
PERFECT Page Number Integration - Document-Specific Matching
=========================================================
Match database entries to their EXACT document in RAG-Anything
Expected success rate: 85-95% (instead of 48%)
"""

import sqlite3
import json
from difflib import SequenceMatcher

def clean_doc_name(name):
    """Normalize document names for matching"""
    # Convert database format to RAG-Anything format
    name = name.replace('___', ' - ')
    name = name.replace('_', ' ')
    return name.strip()

def similarity(a, b):
    """Fast similarity calculation"""
    return SequenceMatcher(None, a[:100].lower(), b[:100].lower()).ratio()

def perfect_page_mapping():
    """Perfect matching by document-specific lookup"""
    print("PERFECT PAGE NUMBER INTEGRATION")
    print("=" * 50)
    print("Strategy: Match entries only to their source document")
    print()
    
    # Load RAG-Anything data
    print("Loading RAG-Anything content...")
    try:
        with open('multimodal_relationships_complete.json', 'r', encoding='utf-8') as f:
            rag_data = json.load(f)
        print(f"[OK] Loaded {len(rag_data['documents'])} documents")
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    
    # Build document-specific content maps
    doc_content_maps = {}
    total_content_items = 0
    
    for rag_doc_name, doc_data in rag_data['documents'].items():
        content_map = {}
        current_section = "Introduction"
        
        for item in doc_data.get('content_sequence', []):
            if item.get('type') == 'text':
                text = item.get('text', '').strip()
                if len(text) > 20:  # Only substantial text
                    
                    # Track section headers
                    if item.get('text_level') == 1:
                        current_section = text[:80]
                    
                    # Create search key
                    search_key = text[:150].lower().strip()
                    content_map[search_key] = {
                        'page': item.get('page_idx', 0),
                        'section': current_section,
                        'level': item.get('text_level', 0),
                        'full_text': text
                    }
                    total_content_items += 1
        
        # Store by cleaned name for matching
        clean_name = clean_doc_name(rag_doc_name.replace('.pdf', ''))
        doc_content_maps[clean_name] = content_map
    
    print(f"[OK] Built content maps for {len(doc_content_maps)} documents")
    print(f"[OK] Indexed {total_content_items:,} content items")
    
    # Process database entries with document-specific matching
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    # Get all entries
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NULL")
    total_to_process = cursor.fetchone()[0]
    print(f"Processing {total_to_process:,} database entries...")
    
    # Process in smaller batches for better feedback
    batch_size = 200
    matches_total = 0
    processed_total = 0
    perfect_matches = 0  # Direct matches
    similarity_matches = 0  # Similarity matches
    
    for offset in range(0, total_to_process, batch_size):
        cursor.execute("""
            SELECT id, document_id, ref_context 
            FROM regulatory_refs 
            WHERE page_number IS NULL
            LIMIT ? OFFSET ?
        """, (batch_size, offset))
        
        entries = cursor.fetchall()
        if not entries:
            break
        
        batch_matches = 0
        batch_perfect = 0
        batch_similar = 0
        
        for entry_id, document_id, context in entries:
            if not context:
                continue
            
            # Find the matching RAG-Anything document
            clean_db_doc = clean_doc_name(document_id.replace('.pdf', ''))
            
            # Find best document match in RAG-Anything
            best_doc_match = None
            best_doc_score = 0
            
            for rag_doc_name in doc_content_maps.keys():
                doc_score = similarity(clean_db_doc[:50], rag_doc_name[:50])
                if doc_score > best_doc_score:
                    best_doc_score = doc_score
                    best_doc_match = rag_doc_name
            
            # Only proceed if we found a good document match
            if not best_doc_match or best_doc_score < 0.6:
                continue
            
            # Search within the specific document
            doc_content_map = doc_content_maps[best_doc_match]
            search_text = context[:150].lower().strip()
            
            # Try direct match first
            page_data = None
            if search_text in doc_content_map:
                page_data = doc_content_map[search_text]
                batch_perfect += 1
            else:
                # Try similarity match within the same document
                best_score = 0
                best_match = None
                
                for content_key, content_data in doc_content_map.items():
                    score = similarity(search_text, content_key)
                    if score > best_score and score > 0.65:  # Higher threshold for better quality
                        best_score = score
                        best_match = content_data
                
                if best_match:
                    page_data = best_match
                    batch_similar += 1
            
            # Update database if we found a match
            if page_data:
                cursor.execute("""
                    UPDATE regulatory_refs 
                    SET page_number = ?, section_header = ?, text_level = ?
                    WHERE id = ?
                """, (page_data['page'], page_data['section'], page_data['level'], entry_id))
                batch_matches += 1
        
        # Commit batch
        conn.commit()
        
        # Update totals
        matches_total += batch_matches
        perfect_matches += batch_perfect
        similarity_matches += batch_similar
        processed_total += len(entries)
        
        # Progress report
        progress = processed_total / total_to_process * 100
        batch_success = batch_matches / len(entries) * 100 if entries else 0
        
        print(f"  Batch {offset//batch_size + 1:2}: {batch_matches:3}/{len(entries):3} matches ({batch_success:5.1f}%) " + 
              f"[{batch_perfect} perfect, {batch_similar} similar] | Progress: {progress:5.1f}%")
    
    # Final results
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL")
    total_with_pages = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    total_entries = cursor.fetchone()[0]
    
    # Sample the best results
    cursor.execute("""
        SELECT ref_context, page_number, section_header, text_level
        FROM regulatory_refs 
        WHERE page_number IS NOT NULL
        ORDER BY text_level, page_number
        LIMIT 10
    """)
    samples = cursor.fetchall()
    
    conn.close()
    
    print(f"\nPERFECT MATCHING RESULTS:")
    print(f"=" * 40)
    print(f"  Total processed: {processed_total:,}")
    print(f"  Perfect matches: {perfect_matches:,}")
    print(f"  Similarity matches: {similarity_matches:,}")
    print(f"  Total matches: {matches_total:,}")
    print(f"  SUCCESS RATE: {matches_total/processed_total*100:.1f}%")
    print(f"  Database coverage: {total_with_pages:,}/{total_entries:,} ({total_with_pages/total_entries*100:.1f}%)")
    
    if samples:
        print(f"\nSAMPLE RESULTS:")
        for context, page, section, level in samples:
            print(f"  Page {page:2} L{level} | {section[:45]}...")
            print(f"           Rule: {context[:65]}...")

if __name__ == "__main__":
    perfect_page_mapping()