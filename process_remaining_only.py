#!/usr/bin/env python3
"""
Process Remaining Documents Only
================================
"""

import json
import sqlite3
import os
import sys
sys.path.append('.')

from ultimate_multimodal_pipeline import UltimateMultimodalPipeline

def process_remaining():
 # Load configuration
 with open('resume_config.json', 'r') as f:
 config = json.load(f)
 
 remaining_docs = config['remaining_documents']
 
 print(f"PROCESSING {len(remaining_docs)} REMAINING DOCUMENTS")
 print("=" * 50)
 
 # Initialize pipeline
 pipeline = UltimateMultimodalPipeline()
 
 # Override document list with only remaining
 pipeline.documents = remaining_docs
 
 # Process with same settings
 pipeline.process_all_documents()
 
 print("\nREMAINING DOCUMENTS PROCESSED!")
 
 # Check final stats
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_refs = cursor.fetchone()[0]
 cursor.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_refs")
 total_docs = cursor.fetchone()[0]
 conn.close()
 
 print(f"\nFINAL DATABASE STATS:")
 print(f" Total references: {total_refs:,}")
 print(f" Total documents: {total_docs}")

if __name__ == "__main__":
 process_remaining()
