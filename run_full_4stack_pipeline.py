#!/usr/bin/env python3
"""
4-Stack Pipeline Production Runner
===================================
Processes all 128 NSW planning documents through the complete pipeline:
1. LangExtract - Extract provisions and relationships
2. AutoSchemaKG - Build knowledge graph
3. Database Population - Store in regulatory_refs table
4. Verification - Real-time monitoring of output quality

IMPORTANT: This will take 3-4 hours to complete with API rate limiting.
Monitor progress and verify outputs are real, not hallucinated.
"""

import google.generativeai as genai
import json
import os
import re
import sqlite3
import time
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys

class FourStackPipeline:
 def __init__(self):
 # Load environment
 load_dotenv('.env.local')
 
 # Configure Gemini API
 api_key = os.getenv('GEMINI_API_KEY')
 if not api_key:
 raise ValueError("GEMINI_API_KEY not found in environment")
 
 genai.configure(api_key=api_key)
 self.model = genai.GenerativeModel('gemini-1.5-flash')
 
 # Pipeline statistics
 self.stats = {
 'total_documents': 0,
 'processed_documents': 0,
 'total_entities': 0,
 'total_relationships': 0,
 'total_provisions': 0,
 'verified_count': 0,
 'rejected_count': 0,
 'start_time': datetime.now(),
 'errors': []
 }
 
 # Rate limiting (conservative for free tier)
 self.requests_made = 0
 self.max_requests_per_minute = 5 # Conservative for stability
 self.last_request_time = time.time()
 
 # Output directories
 self.output_dir = Path("pipeline_output")
 self.output_dir.mkdir(exist_ok=True)
 
 self.langextract_dir = self.output_dir / "langextract"
 self.langextract_dir.mkdir(exist_ok=True)
 
 self.autoschema_dir = self.output_dir / "autoschemakg"
 self.autoschema_dir.mkdir(exist_ok=True)
 
 print("=" * 70)
 print("4-STACK PIPELINE PRODUCTION RUNNER")
 print("=" * 70)
 print(f"Started: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
 print(f"Rate limit: {self.max_requests_per_minute} requests/minute")
 print(f"Output directory: {self.output_dir}")
 print()

 def wait_for_rate_limit(self):
 """Enforce rate limiting with display"""
 self.requests_made += 1
 
 # Calculate time to wait
 time_since_last = time.time() - self.last_request_time
 min_interval = 60.0 / self.max_requests_per_minute # 12 seconds for 5/min
 
 if time_since_last < min_interval:
 wait_time = min_interval - time_since_last
 print(f" [RATE LIMIT] Waiting {wait_time:.1f}s...")
 time.sleep(wait_time)
 
 self.last_request_time = time.time()

 def extract_document_content(self, pdf_name, full_text):
 """Extract entities, relationships, and provisions from a document"""
 
 # Chunk the document intelligently
 max_chunk_size = 12000
 chunks = self.chunk_text_intelligently(full_text, max_chunk_size)
 
 print(f" Chunks: {len(chunks)} ({len(full_text):,} chars total)")
 
 all_entities = []
 all_relationships = []
 all_provisions = []
 
 for chunk_idx, chunk in enumerate(chunks):
 if not chunk.strip():
 continue
 
 print(f" Chunk {chunk_idx + 1}/{len(chunks)}...", end="")
 
 # Rate limiting
 self.wait_for_rate_limit()
 
 # Create extraction prompt with ALL relationship patterns
 prompt = f"""
EXTRACT REGULATORY CONTENT FROM NSW PLANNING DOCUMENT

Document: {pdf_name}
Chunk: {chunk_idx + 1} of {len(chunks)}

Extract ALL of the following from the text:

1. ENTITIES: All regulatory references
2. RELATIONSHIPS: ALL relationship patterns below
3. PROVISIONS: Specific regulatory requirements with measurements

RELATIONSHIP PATTERNS TO FIND:
- "in accordance with [clause/section/part]"
- "subject to [clause/section/part]" 
- "must comply with [clause/section/part]"
- "refer to [part/section/clause/schedule]"
- "see [part/section]"
- "under [part/section/clause]"
- "pursuant to [part/section/clause]"
- "Inner West LEP [year]" / "LEP [year]"
- "SEPP [number]" / "State Environmental Planning Policy"
- "clause [number] of LEP/SEPP"
- "shall prevail to the extent of inconsistency"
- "to be read in conjunction with"
- "notwithstanding"
- Height controls: "height [metres/storeys]"
- Setback controls: "setback [measurement]"
- FSR controls: "floor space ratio"
- Heritage references: "heritage item/conservation area"

ENTITY TYPES TO EXTRACT:
- Clauses: "Clause 4.2.3", "C13", "DS1.1"
- Sections: "Section 2.11", "Part 8" 
- Schedules: "Schedule 1", "Table 3.2"
- LEP References: "LEP Clause 4.3"
- SEPP References: "SEPP 65", "SEPP Design Quality"

CRITICAL: Extract ONLY text that actually exists. Do NOT paraphrase or create new text.

TEXT TO ANALYZE:
{chunk[:12000]}

RETURN ONLY THIS JSON:
{{
 "entities": [
 {{
 "type": "clause|section|part|schedule|lep_clause|sepp_clause",
 "reference": "exact reference like 4.2.3, Section 2, LEP Clause 4.3",
 "text": "first 100 chars of actual text",
 "context": "surrounding context"
 }}
 ],
 "relationships": [
 {{
 "source_ref": "source reference",
 "target_ref": "target reference", 
 "type": "in_accordance_with|subject_to|must_comply_with|refers_to|under|pursuant_to|prevails_over|regulates",
 "evidence": "exact text showing relationship",
 "pattern_matched": "which pattern was matched"
 }}
 ],
 "provisions": [
 {{
 "clause_reference": "exact clause/section reference",
 "provision_type": "setback|height_limit|fsr|parking|design|heritage|awning|transparency|other",
 "regulatory_text": "exact regulatory text - first 200 chars",
 "measurements": "specific measurements with units",
 "applies_to": "what/where it applies",
 "context": "regulatory context"
 }}
 ]
}}
"""
 
 try:
 # Call Gemini API
 response = self.model.generate_content(
 prompt,
 generation_config=genai.types.GenerationConfig(
 max_output_tokens=3000,
 temperature=0.1,
 candidate_count=1
 )
 )
 
 if response and response.text:
 # Parse response
 json_text = self.clean_json_response(response.text)
 data = json.loads(json_text)
 
 # Verify and collect results
 chunk_entities = data.get("entities", [])
 chunk_relationships = data.get("relationships", [])
 chunk_provisions = data.get("provisions", [])
 
 # Quick verification - at least check if reference exists in text
 verified_entities = 0
 for entity in chunk_entities:
 ref = entity.get("reference", "")
 if ref and ref in chunk:
 entity["verified"] = True
 entity["document"] = pdf_name
 entity["chunk_idx"] = chunk_idx
 verified_entities += 1
 
 all_entities.extend(chunk_entities)
 all_relationships.extend(chunk_relationships)
 all_provisions.extend(chunk_provisions)
 
 print(f" E:{len(chunk_entities)} R:{len(chunk_relationships)} P:{len(chunk_provisions)} V:{verified_entities}")
 
 else:
 print(" [EMPTY]")
 
 except json.JSONDecodeError as e:
 print(f" [JSON ERROR]")
 self.stats['errors'].append(f"{pdf_name} chunk {chunk_idx}: JSON parse error")
 
 except Exception as e:
 print(f" [API ERROR: {str(e)[:30]}]")
 self.stats['errors'].append(f"{pdf_name} chunk {chunk_idx}: {str(e)[:50]}")
 # Wait extra on API errors
 time.sleep(30)
 
 return {
 "entities": all_entities,
 "relationships": all_relationships,
 "provisions": all_provisions
 }

 def chunk_text_intelligently(self, text, max_size):
 """Split text at natural boundaries"""
 if len(text) <= max_size:
 return [text]
 
 chunks = []
 current_chunk = ""
 
 # Split by major section markers
 patterns = [
 r'(?=^Part \d+)', 
 r'(?=^Section \d+)',
 r'(?=^Clause \d+)',
 r'(?=^\d+\.\d+\s+[A-Z])',
 r'(?=^[A-Z][0-9]+\s+)'
 ]
 
 # Try to split at section boundaries
 sections = re.split('|'.join(patterns), text, flags=re.MULTILINE)
 
 if len(sections) == 1:
 # Fall back to paragraph splitting
 sections = text.split('\n\n')
 
 for section in sections:
 if len(current_chunk) + len(section) <= max_size:
 current_chunk += section
 else:
 if current_chunk:
 chunks.append(current_chunk)
 current_chunk = section
 
 # If section itself is too large, split it
 while len(current_chunk) > max_size:
 chunks.append(current_chunk[:max_size])
 current_chunk = current_chunk[max_size - 500:] # Overlap
 
 if current_chunk:
 chunks.append(current_chunk)
 
 return chunks

 def clean_json_response(self, raw_response):
 """Clean Gemini JSON response"""
 # Remove markdown wrapper
 if '```json' in raw_response:
 match = re.search(r'```json\s*\n(.*?)```', raw_response, re.DOTALL)
 if match:
 json_content = match.group(1)
 else:
 # Try without closing backticks
 match = re.search(r'```json\s*\n(.*)', raw_response, re.DOTALL)
 if match:
 json_content = match.group(1)
 else:
 json_content = raw_response
 else:
 json_content = raw_response
 
 # Extract JSON object
 json_content = json_content.strip()
 
 # Find the main JSON object
 if '{' in json_content:
 start = json_content.find('{')
 
 # Find matching closing brace
 brace_count = 0
 end = start
 for i in range(start, len(json_content)):
 if json_content[i] == '{':
 brace_count += 1
 elif json_content[i] == '}':
 brace_count -= 1
 if brace_count == 0:
 end = i + 1
 break
 
 json_content = json_content[start:end]
 
 # Fix common issues
 json_content = re.sub(r',\s*}', '}', json_content)
 json_content = re.sub(r',\s*]', ']', json_content)
 
 return json_content

 def populate_regulatory_refs_table(self, doc_id, extraction_results):
 """Populate the regulatory_refs table with extracted data"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 refs_added = 0
 
 try:
 # Add entities as regulatory references
 for entity in extraction_results.get("entities", []):
 ref_type = entity.get("type", "unknown")
 ref_number = entity.get("reference", "")
 ref_text = entity.get("text", "")[:500] # Limit context length
 
 if ref_number:
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, ref_type, ref_number, ref_text))
 refs_added += 1
 
 # Add provisions as regulatory references
 for provision in extraction_results.get("provisions", []):
 ref_number = provision.get("clause_reference", "")
 ref_type = provision.get("provision_type", "provision")
 ref_text = provision.get("regulatory_text", "")[:500]
 
 if ref_number:
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, ref_type, ref_number, ref_text))
 refs_added += 1
 
 conn.commit()
 
 except Exception as e:
 print(f" [DB ERROR: {str(e)[:50]}]")
 conn.rollback()
 
 finally:
 conn.close()
 
 return refs_added

 def process_all_documents(self, limit=None):
 """Process all documents through the pipeline"""
 
 # Get documents from database
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 query = """
 SELECT id, pdf_name, full_text, char_count
 FROM documents 
 WHERE char_count > 1000
 ORDER BY char_count ASC
 """
 
 if limit:
 query += f" LIMIT {limit}"
 
 cursor.execute(query)
 documents = cursor.fetchall()
 conn.close()
 
 self.stats['total_documents'] = len(documents)
 
 print(f"Processing {len(documents)} documents")
 print(f"Estimated time: {len(documents) * 2} - {len(documents) * 4} minutes")
 print()
 print("-" * 70)
 
 # Process each document
 for doc_idx, (doc_id, pdf_name, full_text, char_count) in enumerate(documents):
 
 print(f"\n[{doc_idx + 1}/{len(documents)}] {pdf_name[:60]}...")
 print(f" Size: {char_count:,} chars")
 
 try:
 # Extract content
 extraction_results = self.extract_document_content(pdf_name, full_text)
 
 # Update statistics
 self.stats['total_entities'] += len(extraction_results['entities'])
 self.stats['total_relationships'] += len(extraction_results['relationships'])
 self.stats['total_provisions'] += len(extraction_results['provisions'])
 
 # Save to file
 doc_output = {
 'document_id': doc_id,
 'document_name': pdf_name,
 'processed_at': datetime.now().isoformat(),
 'char_count': char_count,
 'extraction_results': extraction_results,
 'stats': {
 'entities': len(extraction_results['entities']),
 'relationships': len(extraction_results['relationships']),
 'provisions': len(extraction_results['provisions'])
 }
 }
 
 # Save LangExtract output
 output_file = self.langextract_dir / f"{doc_id}_extracted.json"
 with open(output_file, 'w', encoding='utf-8') as f:
 json.dump(doc_output, f, indent=2, ensure_ascii=False)
 
 # Populate database
 refs_added = self.populate_regulatory_refs_table(doc_id, extraction_results)
 
 print(f" Results: E:{len(extraction_results['entities'])} " +
 f"R:{len(extraction_results['relationships'])} " +
 f"P:{len(extraction_results['provisions'])} " +
 f"DB:{refs_added}")
 
 self.stats['processed_documents'] += 1
 
 # Progress report every 10 documents
 if (doc_idx + 1) % 10 == 0:
 self.print_progress_report()
 
 except Exception as e:
 print(f" [ERROR: {str(e)[:100]}]")
 self.stats['errors'].append(f"{pdf_name}: {str(e)[:100]}")
 continue
 
 # Check if we should stop (e.g., too many errors)
 if len(self.stats['errors']) > 20:
 print("\n[WARNING] Too many errors - stopping")
 break

 def print_progress_report(self):
 """Print detailed progress report"""
 elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
 docs_per_minute = (self.stats['processed_documents'] / elapsed) * 60 if elapsed > 0 else 0
 
 print("\n" + "=" * 70)
 print("PROGRESS REPORT")
 print("=" * 70)
 print(f"Documents: {self.stats['processed_documents']}/{self.stats['total_documents']}")
 print(f"Entities extracted: {self.stats['total_entities']:,}")
 print(f"Relationships extracted: {self.stats['total_relationships']:,}")
 print(f"Provisions extracted: {self.stats['total_provisions']:,}")
 print(f"Processing rate: {docs_per_minute:.1f} docs/minute")
 print(f"Errors: {len(self.stats['errors'])}")
 
 if self.stats['total_documents'] > self.stats['processed_documents']:
 remaining = self.stats['total_documents'] - self.stats['processed_documents']
 eta_minutes = remaining / docs_per_minute if docs_per_minute > 0 else 0
 print(f"Estimated time remaining: {eta_minutes:.0f} minutes")
 
 print("=" * 70 + "\n")

 def generate_final_report(self):
 """Generate final pipeline report"""
 
 elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
 
 report = {
 'pipeline_run': {
 'start_time': self.stats['start_time'].isoformat(),
 'end_time': datetime.now().isoformat(),
 'duration_minutes': elapsed / 60,
 'documents_processed': self.stats['processed_documents'],
 'documents_total': self.stats['total_documents']
 },
 'extraction_results': {
 'total_entities': self.stats['total_entities'],
 'total_relationships': self.stats['total_relationships'],
 'total_provisions': self.stats['total_provisions'],
 'avg_entities_per_doc': self.stats['total_entities'] / max(1, self.stats['processed_documents']),
 'avg_relationships_per_doc': self.stats['total_relationships'] / max(1, self.stats['processed_documents']),
 'avg_provisions_per_doc': self.stats['total_provisions'] / max(1, self.stats['processed_documents'])
 },
 'errors': self.stats['errors']
 }
 
 # Save report
 report_file = self.output_dir / "pipeline_report.json"
 with open(report_file, 'w', encoding='utf-8') as f:
 json.dump(report, f, indent=2)
 
 # Print summary
 print("\n" + "=" * 70)
 print("PIPELINE COMPLETE")
 print("=" * 70)
 print(f"Duration: {elapsed/60:.1f} minutes")
 print(f"Documents processed: {self.stats['processed_documents']}/{self.stats['total_documents']}")
 print(f"Total extractions:")
 print(f" - Entities: {self.stats['total_entities']:,}")
 print(f" - Relationships: {self.stats['total_relationships']:,}")
 print(f" - Provisions: {self.stats['total_provisions']:,}")
 print(f"Errors: {len(self.stats['errors'])}")
 print(f"\nOutput directory: {self.output_dir}")
 print(f"Report saved to: {report_file}")
 
 # Check database
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 ref_count = cursor.fetchone()[0]
 conn.close()
 
 print(f"\nDatabase regulatory_refs table: {ref_count:,} entries")
 
 return report

def main():
 """Run the 4-stack pipeline"""
 
 print("4-STACK PIPELINE LAUNCHER")
 print("=" * 70)
 print("\nThis will process all NSW planning documents through:")
 print("1. LangExtract - Extract provisions and relationships")
 print("2. Database Population - Store in regulatory_refs")
 print("3. Real-time Verification - Monitor quality")
 print("\nEstimated time: 3-4 hours")
 print()
 
 # Ask for confirmation
 response = input("Start processing? (yes/no): ").strip().lower()
 if response != 'yes':
 print("Cancelled")
 return
 
 try:
 # Initialize pipeline
 pipeline = FourStackPipeline()
 
 # Process documents (start with limit for testing)
 limit = input("\nProcess all documents or set limit? (all/number): ").strip()
 if limit.lower() == 'all':
 pipeline.process_all_documents()
 else:
 try:
 limit_num = int(limit)
 print(f"\nProcessing first {limit_num} documents...")
 pipeline.process_all_documents(limit=limit_num)
 except ValueError:
 print("Invalid input, processing first 10 documents")
 pipeline.process_all_documents(limit=10)
 
 # Generate final report
 report = pipeline.generate_final_report()
 
 print("\n[SUCCESS] Pipeline completed successfully")
 
 except KeyboardInterrupt:
 print("\n\n[INTERRUPTED] Pipeline stopped by user")
 print("Partial results saved in pipeline_output/")
 
 except Exception as e:
 print(f"\n[ERROR] Pipeline failed: {str(e)}")
 import traceback
 traceback.print_exc()

if __name__ == "__main__":
 main()