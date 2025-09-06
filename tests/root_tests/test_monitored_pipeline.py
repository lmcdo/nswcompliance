#!/usr/bin/env python3
"""
Test Monitored Pipeline on 5 Documents
======================================
"""

from monitored_4stack_pipeline import MonitoredPipeline
import sqlite3

def test_monitoring():
    """Test monitoring system on 5 documents"""
    
    print("TESTING MONITORED PIPELINE")
    print("=" * 50)
    
    try:
        pipeline = MonitoredPipeline()
        
        # Get 5 documents 
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, pdf_name, full_text, char_count
            FROM documents 
            WHERE char_count BETWEEN 5000 AND 25000
            ORDER BY char_count ASC
            LIMIT 5
        """)
        documents = cursor.fetchall()
        conn.close()
        
        pipeline.stats['total_documents'] = len(documents)
        
        print(f"Testing on {len(documents)} documents:")
        for i, (doc_id, pdf_name, _, char_count) in enumerate(documents):
            print(f"  {i+1}: {pdf_name[:50]}... ({char_count:,} chars)")
        print()
        
        # Process documents
        for doc_idx, (doc_id, pdf_name, full_text, char_count) in enumerate(documents):
            print(f"\n[{doc_idx + 1}/5] Processing {pdf_name[:60]}...")
            
            extraction_results = pipeline.extract_from_document(doc_id, pdf_name, full_text)
            
            # Update stats
            pipeline.stats['total_entities'] += len(extraction_results['entities'])
            pipeline.stats['total_relationships'] += len(extraction_results['relationships'])
            pipeline.stats['total_provisions'] += len(extraction_results['provisions'])
            
            # Update database
            db_entries = pipeline.update_database(doc_id, extraction_results)
            pipeline.stats['db_entries_added'] += db_entries
            pipeline.stats['processed_documents'] += 1
            
            print(f"  Results: E:{len(extraction_results['entities'])} R:{len(extraction_results['relationships'])} P:{len(extraction_results['provisions'])} DB:{db_entries}")
        
        # Final report
        pipeline.print_progress_report()
        pipeline.save_progress()
        
        # Check database
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
        final_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"\nTEST COMPLETE:")
        print(f"- Total entities: {pipeline.stats['total_entities']}")
        print(f"- Total relationships: {pipeline.stats['total_relationships']}")
        print(f"- Total provisions: {pipeline.stats['total_provisions']}")
        print(f"- Database entries: {final_count:,}")
        print(f"- API calls: {pipeline.stats['total_api_calls']}")
        
        if pipeline.stats['total_entities'] > 0:
            print("\n[SUCCESS] Monitoring system working - ready for full run")
            return True
        else:
            print("\n[WARNING] No extractions - check system")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_monitoring()
    if success:
        print("\nTo start full pipeline: python monitored_4stack_pipeline.py")
    else:
        print("\nFix issues before full run")