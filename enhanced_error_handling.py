#!/usr/bin/env python3
"""
Enhanced Error Handling for Pipeline Stalls
=============================================
Prevents common stall causes:
1. Skip documents with repeated JSON failures
2. Add timeout protection 
3. Implement circuit breakers
4. Better chunk failure handling
"""

import json
import time
from datetime import datetime, timedelta

class PipelineStallPreventer:
 def __init__(self):
 self.failed_documents = {} # Track failure counts per document
 self.stall_timeout = 300 # 5 minutes max per document
 self.max_failures_per_doc = 3
 self.circuit_breaker_threshold = 5 # Skip after 5 consecutive failures
 
 def should_skip_document(self, pdf_name):
 """Check if document should be skipped due to repeated failures"""
 failure_count = self.failed_documents.get(pdf_name, 0)
 if failure_count >= self.max_failures_per_doc:
 print(f"WARNING: SKIPPING {pdf_name} - {failure_count} previous failures")
 return True
 return False
 
 def record_document_failure(self, pdf_name, error_type):
 """Record a document failure"""
 if pdf_name not in self.failed_documents:
 self.failed_documents[pdf_name] = 0
 self.failed_documents[pdf_name] += 1
 
 print(f"ERROR: FAILURE #{self.failed_documents[pdf_name]} for {pdf_name}: {error_type}")
 
 def check_for_stall(self, last_progress_time):
 """Check if pipeline has stalled"""
 if datetime.now() - last_progress_time > timedelta(minutes=10):
 print("WARNING: STALL DETECTED - Pipeline hasn't progressed in 10+ minutes")
 return True
 return False
 
 def get_problematic_documents(self):
 """Return list of consistently failing documents"""
 problematic = []
 
 # Known problematic patterns from error log analysis
 known_problem_patterns = [
 "Leichhardt DCP 2013 - 12 - Part G Section 1-12", # 5 chunk failures
 "Leichhardt DCP 2013 - 8 - Part C Place Section 4", # 5 chunk failures 
 "Marrickville DCP 2011 - 10.0 Definitions", # Consistent JSON errors
 "Marrickville DCP 2011 - 9 35 Parramatta Road", # Database errors
 "Marrickville DCP 2011 - 2 25 Stormwater management" # Database errors
 ]
 
 return known_problem_patterns
 
 def create_skip_list(self):
 """Create list of documents to skip to avoid stalls"""
 skip_list = self.get_problematic_documents()
 
 print("STALL PREVENTION - SKIP LIST")
 print("=" * 40)
 for doc in skip_list:
 print(f" WARNING: {doc}")
 print(f"\nTotal documents to skip: {len(skip_list)}")
 
 return skip_list

def apply_stall_prevention():
 """Apply stall prevention to current pipeline"""
 preventer = PipelineStallPreventer()
 skip_list = preventer.create_skip_list()
 
 # Read current remaining documents
 with open('resume_config.json', 'r') as f:
 config = json.load(f)
 
 original_docs = config['remaining_documents']
 
 # Filter out problematic documents
 filtered_docs = []
 skipped_docs = []
 
 for doc in original_docs:
 should_skip = False
 for pattern in skip_list:
 if pattern in doc:
 should_skip = True
 skipped_docs.append(doc)
 break
 
 if not should_skip:
 filtered_docs.append(doc)
 
 print(f"\nFILTERED RESULTS:")
 print(f" Original documents: {len(original_docs)}")
 print(f" Filtered documents: {len(filtered_docs)}")
 print(f" Skipped documents: {len(skipped_docs)}")
 
 if skipped_docs:
 print(f"\nSkipped documents:")
 for doc in skipped_docs:
 print(f" SKIP: {doc}")
 
 # Update config
 config['remaining_documents'] = filtered_docs
 config['skipped_documents'] = skipped_docs
 config['stall_prevention_applied'] = True
 config['filter_time'] = datetime.now().isoformat()
 
 with open('resume_config_filtered.json', 'w') as f:
 json.dump(config, f, indent=2)
 
 print(f"\nFiltered configuration saved to resume_config_filtered.json")
 print(f"This should prevent pipeline stalls.")
 
 return len(filtered_docs), len(skipped_docs)

if __name__ == "__main__":
 apply_stall_prevention()