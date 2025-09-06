#!/usr/bin/env python3
"""
Auto-Start Full Pipeline
=======================
Start the full 4-stack pipeline without prompts
"""

from monitored_4stack_pipeline import MonitoredPipeline

def start_full_pipeline():
    """Start the full pipeline automatically"""
    
    print("AUTO-STARTING FULL 4-STACK PIPELINE")
    print("=" * 60)
    print("Processing all 128 documents with monitoring...")
    print()
    
    try:
        pipeline = MonitoredPipeline()
        
        print("STARTING FULL PIPELINE PROCESSING...")
        print("Expected duration: 4.3 hours")
        print("Progress reports every 10 minutes")
        print("Press Ctrl+C for graceful shutdown")
        print()
        
        # Process all documents
        pipeline.process_all_documents()
        
        # Generate final report
        pipeline.generate_final_report()
        
        print("\n[SUCCESS] Full pipeline completed!")
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Pipeline stopped by user")
        pipeline.save_progress()
        print("Progress saved. Use resume functionality to continue.")
        
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    start_full_pipeline()