#!/usr/bin/env python3
"""
Test 4-Stack Pipeline on Small Batch
====================================
Test the pipeline on just 3 documents to verify it works before the full run.
"""

from run_full_4stack_pipeline import FourStackPipeline
import sqlite3

def test_small_batch():
    """Test pipeline on 3 small documents"""
    
    print("TESTING 4-STACK PIPELINE ON SMALL BATCH")
    print("=" * 60)
    print("Processing 3 documents to verify methodology works")
    print()
    
    try:
        # Initialize pipeline
        pipeline = FourStackPipeline()
        
        # Process just 3 documents
        pipeline.process_all_documents(limit=3)
        
        # Generate report
        report = pipeline.generate_final_report()
        
        # Check database results
        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
        ref_count = cursor.fetchone()[0]
        conn.close()
        
        print(f"\nTEST RESULTS:")
        print(f"Documents processed: {pipeline.stats['processed_documents']}")
        print(f"Entities extracted: {pipeline.stats['total_entities']}")
        print(f"Relationships extracted: {pipeline.stats['total_relationships']}")
        print(f"Provisions extracted: {pipeline.stats['total_provisions']}")
        print(f"Database entries: {ref_count}")
        print(f"Errors: {len(pipeline.stats['errors'])}")
        
        if pipeline.stats['total_entities'] > 0 and pipeline.stats['total_relationships'] > 0:
            print("\n[SUCCESS] Pipeline test completed - ready for full run")
            return True
        else:
            print("\n[WARNING] Low extraction counts - review before full run")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Pipeline test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_small_batch()
    if success:
        print("\nNext step: Run on all 128 documents")
    else:
        print("\nFix issues before full run")