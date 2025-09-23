#!/usr/bin/env python3
"""
Resume Processing Remaining Documents
=====================================
Process the 12 documents that didn't complete
"""

import sqlite3
import json
import os
from datetime import datetime

def find_remaining_documents():
 """Identify which documents haven't been processed"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get all documents from documents table
 cursor.execute("SELECT pdf_name FROM documents ORDER BY char_count")
 all_docs = [r[0] for r in cursor.fetchall()]
 
 # Get processed document IDs from regulatory_refs
 cursor.execute("SELECT DISTINCT document_id FROM regulatory_refs")
 processed_ids = set([r[0] for r in cursor.fetchall()])
 
 conn.close()
 
 # Convert document names to IDs for comparison
 remaining = []
 for doc_name in all_docs:
 # Convert to ID format used in regulatory_refs
 doc_id = doc_name.replace('.pdf', '').replace(' ', '_').replace('-', '_')
 
 # Check if this document has been processed
 found = False
 for proc_id in processed_ids:
 if doc_id in proc_id or proc_id in doc_id:
 found = True
 break
 
 if not found:
 remaining.append(doc_name)
 
 return remaining

def process_remaining_documents():
 """Process only the remaining documents"""
 
 remaining = find_remaining_documents()
 
 print("REMAINING DOCUMENTS TO PROCESS")
 print("=" * 50)
 for i, doc in enumerate(remaining, 1):
 print(f"{i:2}. {doc}")
 
 print(f"\nTotal: {len(remaining)} documents")
 
 if not remaining:
 print("All documents have been processed!")
 return
 
 # Create resume configuration
 resume_config = {
 "remaining_documents": remaining,
 "start_time": datetime.now().isoformat(),
 "total_count": len(remaining)
 }
 
 with open('resume_config.json', 'w') as f:
 json.dump(resume_config, f, indent=2)
 
 print("\nConfiguration saved to resume_config.json")
 print("\nTo process remaining documents, run:")
 print("python process_remaining_only.py")
 
 return remaining

def create_resume_processor():
 """Create the script to process remaining documents"""
 
 processor_code = '''#!/usr/bin/env python3
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
 
 print("\\nREMAINING DOCUMENTS PROCESSED!")
 
 # Check final stats
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_refs = cursor.fetchone()[0]
 cursor.execute("SELECT COUNT(DISTINCT document_id) FROM regulatory_refs")
 total_docs = cursor.fetchone()[0]
 conn.close()
 
 print(f"\\nFINAL DATABASE STATS:")
 print(f" Total references: {total_refs:,}")
 print(f" Total documents: {total_docs}")

if __name__ == "__main__":
 process_remaining()
'''
 
 with open('process_remaining_only.py', 'w') as f:
 f.write(processor_code)
 
 print("Created process_remaining_only.py")

if __name__ == "__main__":
 remaining = process_remaining_documents()
 if remaining:
 create_resume_processor()
 print("\n" + "=" * 50)
 print("READY TO RESUME")
 print("=" * 50)
 print("Run this command to process remaining documents:")
 print("\nset PYTHONIOENCODING=utf-8 && set PYTHONUTF8=1 && ./venv_linux/Scripts/python.exe process_remaining_only.py")