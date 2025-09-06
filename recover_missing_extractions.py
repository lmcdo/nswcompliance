#!/usr/bin/env python3
"""
Recover Missing Extractions
===========================
Re-process the 36 documents that were successfully extracted in the previous run
but not saved to database due to missing process_all_documents method.
"""

import json
import sqlite3
import re
from ultimate_multimodal_pipeline import UltimateMultimodalPipeline

def get_missing_documents():
    """Get list of documents processed but not saved to database"""
    
    # Read error log to find successfully processed documents
    with open('monitored_pipeline_output/errors.log', 'r', encoding='utf-8') as f:
        log_content = f.read()

    # Find all successful completions between 18:10 and 18:25
    pattern = r'\[2025-09-01 18:(1[0-9]|2[0-5]):\d+\] (.+?): \'entities\''
    matches = re.findall(pattern, log_content)

    processed_docs = []
    for time_match, doc_name in matches:
        if int(time_match) <= 25:  # Up to 18:25
            processed_docs.append(doc_name.strip())

    return list(set(processed_docs))  # Remove duplicates

def recover_extractions():
    """Re-process missing documents and add to database"""
    
    missing_docs = get_missing_documents()
    print(f"RECOVERING {len(missing_docs)} MISSING EXTRACTIONS")
    print("=" * 60)
    
    # Get document IDs for missing docs
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    
    placeholders = ','.join(['?' for _ in missing_docs])
    cursor.execute(f"""
        SELECT id, pdf_name, full_text 
        FROM documents 
        WHERE pdf_name IN ({placeholders})
        ORDER BY char_count
    """, missing_docs)
    
    missing_doc_data = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(missing_doc_data)} documents to recover")
    
    if not missing_doc_data:
        print("No missing documents found in database")
        return
    
    # Initialize pipeline
    pipeline = UltimateMultimodalPipeline()
    
    total_entries_added = 0
    
    for idx, (doc_id, pdf_name, full_text) in enumerate(missing_doc_data, 1):
        try:
            print(f"\n[{idx}/{len(missing_doc_data)}] Recovering: {pdf_name[:60]}...")
            
            # Extract content  
            results = pipeline.extract_from_document(doc_id, pdf_name, full_text)
            
            # Update database
            entries_added = pipeline.update_database(doc_id, results)
            total_entries_added += entries_added
            
            print(f"  Added {entries_added} database entries")
            
            # Show extraction summary
            formal_count = len(results.get('formal_entities', []))
            context_count = len(results.get('contextual_information', []))
            informal_count = len(results.get('informal_regulatory', []))
            relationship_count = len(results.get('relationships', []))
            
            if formal_count + context_count + informal_count + relationship_count > 0:
                print(f"  Extracted: F:{formal_count} C:{context_count} I:{informal_count} R:{relationship_count}")
            else:
                print("  [No regulatory content found]")
                
        except Exception as e:
            print(f"  ERROR: {str(e)}")
            continue
    
    # Final database check
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
    final_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"\n" + "=" * 60)
    print("RECOVERY COMPLETE")
    print("=" * 60)
    print(f"Documents recovered: {len(missing_doc_data)}")
    print(f"Database entries added: {total_entries_added}")
    print(f"Final database size: {final_count:,} references")
    
    return total_entries_added

if __name__ == "__main__":
    recovery_count = recover_extractions()
    if recovery_count > 0:
        print(f"\n✅ Successfully recovered {recovery_count} missing extractions")
    else:
        print(f"\n❌ No extractions recovered")