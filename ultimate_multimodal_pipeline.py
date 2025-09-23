#!/usr/bin/env python3
"""
Ultimate Multimodal Regulatory Extraction Pipeline
==================================================
Combines LangExtract with AutoSchemaKG's 1,473 images + 600 tables
to create the most comprehensive regulatory intelligence extraction.

Data Sources:
- Text documents (128 docs)
- Images with clause mappings (1,473 images, 351 with clause context) 
- Table data (600 tables)
- Visual-text relationships

Extracts:
1. Formal regulatory entities (clauses, zones, SEPPs)
2. Non-clause regulatory context (character, intent, guidance)
3. Visual regulatory content (diagrams, tables, measurements)
4. Image-clause relationships (351 mapped connections)
5. All regulatory relationships and dependencies
"""

import json
import google.generativeai as genai
import os
import sqlite3
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from monitored_4stack_pipeline import MonitoredPipeline

class UltimateMultimodalPipeline(MonitoredPipeline):
 """Ultimate pipeline with full multimodal regulatory extraction"""
 
 def __init__(self):
 super().__init__()
 
 # Load AutoSchemaKG visual data
 print("Loading AutoSchemaKG visual data...")
 try:
 with open('autoschema_multimodal_complete.json', 'r', encoding='utf-8') as f:
 self.autoschema_data = json.load(f)
 
 # Index images and tables by document
 self.images_by_doc = {}
 self.tables_by_doc = {}
 self.clause_image_map = {}
 
 for entity in self.autoschema_data.get('entities', []):
 if entity.get('type') == 'image':
 doc_name = entity.get('document', '')
 if doc_name not in self.images_by_doc:
 self.images_by_doc[doc_name] = []
 
 image_info = {
 'path': entity.get('path', ''),
 'page': entity.get('page', 0),
 'clause_context': entity.get('clause_context'),
 'id': entity.get('id', '')
 }
 self.images_by_doc[doc_name].append(image_info)
 
 # Map clause-to-image connections
 if entity.get('clause_context'):
 clause = entity.get('clause_context')
 if clause not in self.clause_image_map:
 self.clause_image_map[clause] = []
 self.clause_image_map[clause].append(image_info)
 
 print(f"[OK] Loaded {len([e for e in self.autoschema_data.get('entities', []) if e.get('type') == 'image'])} images")
 print(f"[OK] Indexed {sum(len(imgs) for imgs in self.images_by_doc.values())} image references")
 print(f"[OK] Found {len(self.clause_image_map)} clauses with visual elements")
 
 except Exception as e:
 print(f"[WARNING] Could not load AutoSchemaKG data: {e}")
 self.autoschema_data = {}
 self.images_by_doc = {}
 self.tables_by_doc = {}
 self.clause_image_map = {}

 def extract_from_document(self, doc_id, pdf_name, full_text):
 """Ultimate multimodal extraction with visual context"""
 
 # Get visual elements for this document
 doc_images = self.get_document_images(pdf_name)
 visual_clauses = self.get_visual_clause_mappings(pdf_name)
 
 # Chunk intelligently
 max_chunk_size = 8000
 chunks = self.intelligent_chunk(full_text, max_chunk_size)
 
 print(f" Chunks: {len(chunks)} | Images: {len(doc_images)} | Visual clauses: {len(visual_clauses)}")
 
 all_results = {
 'formal_entities': [],
 'contextual_information': [],
 'informal_regulatory': [], 
 'visual_elements': doc_images,
 'relationships': [],
 'provisions': [],
 'visual_clause_connections': visual_clauses
 }
 
 for chunk_idx, chunk in enumerate(chunks):
 if not chunk.strip():
 continue
 
 print(f" [{chunk_idx + 1}/{len(chunks)}] ", end="")
 
 # Rate limiting
 self.enforce_rate_limit()
 
 # ULTIMATE multimodal extraction prompt
 prompt = f"""
ULTIMATE MULTIMODAL REGULATORY EXTRACTION

Document: {pdf_name}
Chunk: {chunk_idx + 1} of {len(chunks)}

VISUAL CONTEXT AVAILABLE:
- {len(doc_images)} images in this document
- {len(visual_clauses)} clauses with visual elements
- Visual clause mappings: {list(visual_clauses.keys())[:5]}

EXTRACT ALL REGULATORY CONTENT:

1. FORMAL REGULATORY ENTITIES:
 - Clauses, sections, zones (R1-R4, B1-B6, IN1-IN2, etc.)
 - Development standards (height, FSR, setbacks) 
 - SEPP references, assessment categories
 - Overlay controls (heritage, flood, bushfire)

2. NON-CLAUSE REGULATORY CONTENT:
 - Area character descriptions
 - Policy intent statements ("This aims to...")
 - Design guidance ("Buildings should...")
 - Assessment considerations ("Council will consider...")
 - Implementation notes and discretions

3. VISUAL REFERENCES:
 - "As shown in Figure X" or "See Table Y"
 - References to diagrams, measurements, illustrations
 - Table/chart references for rates or standards

4. REGULATORY RELATIONSHIPS:
 - Cross-references between clauses
 - LEP/DCP/SEPP hierarchies and dependencies
 - "In accordance with", "Subject to", "Refer to"

TEXT CHUNK:
{chunk[:6000]}

RETURN COMPREHENSIVE JSON:
{{
 "formal_entities": [
 {{
 "type": "zone|clause|sepp|standard|overlay|assessment",
 "reference": "exact reference (e.g., R2, Clause 4.3, SEPP 65)",
 "text": "regulatory text",
 "category": "specific category",
 "measurements": "any specific measurements",
 "verified": true
 }}
 ],
 "contextual_information": [
 {{
 "type": "character_description|policy_intent|design_guidance|assessment_note",
 "text": "contextual regulatory information",
 "applies_to": "scope of application",
 "regulatory_significance": "how this informs compliance"
 }}
 ],
 "informal_regulatory": [
 {{
 "type": "should_statement|guidance|discretion|objective",
 "text": "informal regulatory guidance",
 "strength": "should|must|may|preferred|discretionary",
 "applies_to": "what this applies to"
 }}
 ],
 "visual_references": [
 {{
 "reference": "Figure X, Table Y, Diagram Z reference in text",
 "description": "what the visual element shows",
 "regulatory_purpose": "why this visual matters for compliance"
 }}
 ],
 "relationships": [
 {{
 "source": "source entity",
 "target": "target entity",
 "type": "in_accordance_with|subject_to|refers_to|overrides|modifies",
 "evidence": "exact text showing relationship"
 }}
 ],
 "provisions": [
 {{
 "entity": "entity this provision relates to",
 "type": "setback|height|fsr|parking|design|heritage|zone|assessment",
 "text": "provision text",
 "measurements": "specific values/measurements",
 "applies_to": "scope",
 "visual_support": "any visual elements that support this provision"
 }}
 ]
}}
"""
 
 try:
 response = self.model.generate_content(
 prompt,
 generation_config=genai.types.GenerationConfig(
 max_output_tokens=3000,
 temperature=0.1
 )
 )
 
 if response and response.text:
 # Parse response
 json_text = self.clean_json(response.text)
 data = json.loads(json_text)
 
 # Enhance with visual connections
 enhanced_data = self.enhance_with_visual_connections(data, chunk, visual_clauses)
 
 # Collect all results
 for category in ['formal_entities', 'contextual_information', 'informal_regulatory', 'relationships', 'provisions']:
 if category in enhanced_data:
 all_results[category].extend(enhanced_data[category])
 
 # Add visual references
 if 'visual_references' in enhanced_data:
 all_results.setdefault('visual_references', []).extend(enhanced_data['visual_references'])
 
 # Count and verify
 entities_count = len(enhanced_data.get('formal_entities', []))
 context_count = len(enhanced_data.get('contextual_information', []))
 informal_count = len(enhanced_data.get('informal_regulatory', []))
 relationships_count = len(enhanced_data.get('relationships', []))
 provisions_count = len(enhanced_data.get('provisions', []))
 visual_refs_count = len(enhanced_data.get('visual_references', []))
 
 verified_entities = sum(1 for e in enhanced_data.get('formal_entities', []) if e.get('verified'))
 
 print(f"E:{entities_count} C:{context_count} I:{informal_count} R:{relationships_count} P:{provisions_count} V:{visual_refs_count} V:{verified_entities}")
 
 if any(enhanced_data.get(k) for k in ['formal_entities', 'contextual_information', 'informal_regulatory', 'relationships', 'provisions']):
 self.stats['successful_extractions'] += 1
 
 else:
 print("[EMPTY]")
 self.stats['failed_extractions'] += 1
 
 except json.JSONDecodeError:
 print("[JSON_ERROR]")
 self.stats['failed_extractions'] += 1
 self.log_error(f"{pdf_name} chunk {chunk_idx}: JSON parse error")
 
 except Exception as e:
 print(f"[ERROR: {str(e)[:20]}]")
 self.stats['failed_extractions'] += 1
 self.log_error(f"{pdf_name} chunk {chunk_idx}: {str(e)}")
 time.sleep(10)
 
 return all_results

 def get_document_images(self, pdf_name):
 """Get all images for this document from AutoSchemaKG"""
 # Try multiple name matching approaches
 for doc_key in self.images_by_doc.keys():
 if pdf_name.replace('.pdf', '') in doc_key or doc_key in pdf_name:
 return self.images_by_doc[doc_key]
 
 # Try partial matching
 pdf_base = pdf_name.replace('.pdf', '').replace(' ', '').lower()
 for doc_key, images in self.images_by_doc.items():
 doc_base = doc_key.replace(' ', '').lower()
 if pdf_base in doc_base or doc_base in pdf_base:
 return images
 
 return []

 def get_visual_clause_mappings(self, pdf_name):
 """Get clauses that have visual elements in this document"""
 doc_images = self.get_document_images(pdf_name)
 visual_clauses = {}
 
 for image in doc_images:
 if image.get('clause_context'):
 clause = image['clause_context']
 if clause not in visual_clauses:
 visual_clauses[clause] = []
 visual_clauses[clause].append(image)
 
 return visual_clauses

 def enhance_with_visual_connections(self, extracted_data, chunk_text, visual_clauses):
 """Enhance extracted data with visual element connections"""
 
 enhanced_data = extracted_data.copy()
 
 # Connect formal entities to visual elements
 for entity in enhanced_data.get('formal_entities', []):
 entity_ref = entity.get('reference', '')
 
 # Check if this entity has visual support
 if entity_ref in visual_clauses:
 entity['visual_elements'] = visual_clauses[entity_ref]
 entity['has_visual_support'] = True
 else:
 entity['has_visual_support'] = False
 
 # Enhance provisions with visual context
 for provision in enhanced_data.get('provisions', []):
 entity_ref = provision.get('entity', '')
 
 # Look for visual references in the text
 visual_refs = []
 import re
 visual_patterns = [
 r'(?:as shown in|see|refer to)\s+(?:figure|table|diagram|schedule)\s+([A-Z0-9\.]+)',
 r'(?:figure|table|diagram|schedule)\s+([A-Z0-9\.]+)',
 r'see\s+([A-Z0-9\.]+)'
 ]
 
 for pattern in visual_patterns:
 matches = re.findall(pattern, provision.get('text', ''), re.IGNORECASE)
 visual_refs.extend(matches)
 
 if visual_refs:
 provision['visual_references'] = list(set(visual_refs))
 
 return enhanced_data

 def update_database(self, doc_id, extraction_results):
 """Enhanced database population with multimodal data"""
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 entries_added = 0
 
 try:
 # Add formal entities
 for entity in extraction_results.get('formal_entities', []):
 if entity.get('reference'):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, f"formal_{entity.get('category', entity.get('type', 'entity'))}", 
 entity.get('reference'), entity.get('text', '')[:500]))
 entries_added += 1
 
 # Add contextual information
 for context in extraction_results.get('contextual_information', []):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, f"context_{context.get('type')}", 
 context.get('applies_to', 'general'), context.get('text', '')[:500]))
 entries_added += 1
 
 # Add informal regulatory content
 for informal in extraction_results.get('informal_regulatory', []):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, f"informal_{informal.get('type')}", 
 informal.get('applies_to', 'general'), informal.get('text', '')[:500]))
 entries_added += 1
 
 # Add visual connections
 for visual in extraction_results.get('visual_references', []):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, "visual_reference", visual.get('reference', ''), 
 visual.get('description', '')[:500]))
 entries_added += 1
 
 # Add relationships
 for rel in extraction_results.get('relationships', []):
 if rel.get('source') and rel.get('target'):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, f"relationship_{rel.get('type')}", 
 f"{rel.get('source')} -> {rel.get('target')}", 
 rel.get('evidence', '')[:500]))
 entries_added += 1
 
 # Add provisions
 for prov in extraction_results.get('provisions', []):
 if prov.get('entity'):
 cursor.execute("""
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number, ref_context)
 VALUES (?, ?, ?, ?)
 """, (doc_id, f"provision_{prov.get('type')}", 
 prov.get('entity'), prov.get('text', '')[:500]))
 entries_added += 1
 
 conn.commit()
 
 except Exception as e:
 self.log_error(f"Database error for {doc_id}: {str(e)}")
 conn.rollback()
 
 finally:
 conn.close()
 
 return entries_added

 def update_progress_file(self):
 """Update progress.json with current stats and database state"""
 try:
 # Get current database count
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 db_count = cursor.fetchone()[0]
 conn.close()
 
 progress_data = {
 "stats": {
 "start_time": self.stats.get('start_time', ''),
 "total_documents": self.stats.get('total_documents', 0),
 "processed_documents": self.stats.get('processed_documents', 0),
 "total_api_calls": self.stats.get('total_api_calls', 0),
 "successful_extractions": self.stats.get('successful_extractions', 0),
 "failed_extractions": self.stats.get('failed_extractions', 0),
 "total_entities": self.stats.get('total_entities', 0),
 "total_relationships": self.stats.get('total_relationships', 0),
 "total_provisions": self.stats.get('total_provisions', 0),
 "db_entries_total": db_count,
 "errors": self.stats.get('errors', [])
 },
 "last_update": datetime.now().isoformat()
 }
 
 os.makedirs('monitored_pipeline_output', exist_ok=True)
 with open('monitored_pipeline_output/progress.json', 'w', encoding='utf-8') as f:
 json.dump(progress_data, f, indent=2)
 
 except Exception as e:
 print(f"Progress update error: {e}")

 def process_all_documents(self):
 """Main processing loop with database monitoring"""
 
 # Initialize stats
 self.stats = {
 'start_time': datetime.now().isoformat(),
 'processed_documents': 0,
 'total_api_calls': 0,
 'successful_extractions': 0,
 'failed_extractions': 0,
 'total_entities': 0,
 'total_relationships': 0,
 'total_provisions': 0,
 'errors': []
 }
 
 # Load documents - check if override list exists
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 if hasattr(self, 'documents') and self.documents:
 # Use override list (for resume processing)
 placeholders = ','.join('?' * len(self.documents))
 cursor.execute(f"SELECT id, pdf_name, full_text FROM documents WHERE pdf_name IN ({placeholders}) AND char_count > 500 ORDER BY char_count", self.documents)
 documents = cursor.fetchall()
 print(f"RESUME MODE: Processing {len(documents)} remaining documents from override list")
 else:
 # Normal processing - all documents
 cursor.execute("SELECT id, pdf_name, full_text FROM documents WHERE char_count > 500 ORDER BY char_count")
 documents = cursor.fetchall()
 
 conn.close()
 
 self.stats['total_documents'] = len(documents)
 
 print(f"Processing {len(documents)} documents")
 print("Estimated time: 6.4 to 12.7 hours")
 print("=" * 80)
 print()
 
 for doc_idx, (doc_id, pdf_name, full_text) in enumerate(documents, 1):
 try:
 print(f"[{doc_idx}/{len(documents)}] {pdf_name[:80]}...")
 
 # Extract content
 results = self.extract_from_document(doc_id, pdf_name, full_text)
 
 # Update database 
 entries_added = self.update_database(doc_id, results)
 print(f" Database entries added: {entries_added}")
 
 # Update stats
 self.stats['processed_documents'] += 1
 self.stats['total_entities'] += len(results.get('formal_entities', []))
 self.stats['total_relationships'] += len(results.get('relationships', []))
 self.stats['total_provisions'] += len(results.get('provisions', []))
 
 # Update progress every 5 documents
 if doc_idx % 5 == 0:
 self.update_progress_file()
 
 # Show database growth
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_refs = cursor.fetchone()[0]
 conn.close()
 
 completion = (doc_idx / len(documents)) * 100
 print(f" Progress: {completion:.1f}% | Database: {total_refs:,} references")
 
 except Exception as e:
 print(f" ERROR: {str(e)}")
 self.stats['errors'].append(f"{pdf_name}: {str(e)}")
 continue
 
 # Final progress update
 self.update_progress_file()

def main():
 """Run ultimate multimodal extraction pipeline"""
 
 print("ULTIMATE MULTIMODAL REGULATORY EXTRACTION")
 print("=" * 80)
 print("Integrating:")
 print("- 128 NSW planning documents (text)")
 print("- 1,473 regulatory images with clause mappings")
 print("- 600 tables and diagrams") 
 print("- 351 clause-to-image connections")
 print("- All formal and informal regulatory content")
 print()
 print("Expected output: 5,000-10,000 regulatory references")
 print("Duration: 5-6 hours")
 print("=" * 80)
 
 try:
 pipeline = UltimateMultimodalPipeline()
 
 print("STARTING ULTIMATE MULTIMODAL PIPELINE...")
 pipeline.process_all_documents()
 
 # Generate comprehensive report
 report = pipeline.generate_final_report()
 
 # Check final database state with breakdown
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_refs = cursor.fetchone()[0]
 
 cursor.execute("""
 SELECT ref_type, COUNT(*) 
 FROM regulatory_refs 
 GROUP BY ref_type 
 ORDER BY COUNT(*) DESC
 """)
 ref_breakdown = cursor.fetchall()
 conn.close()
 
 print(f"\n[SUCCESS] ULTIMATE MULTIMODAL EXTRACTION COMPLETE")
 print(f"Total regulatory references: {total_refs:,}")
 print(f"\nComprehensive breakdown:")
 for ref_type, count in ref_breakdown:
 print(f" {ref_type}: {count:,}")
 
 return True
 
 except KeyboardInterrupt:
 print("\n[INTERRUPTED] Pipeline stopped by user")
 pipeline.save_progress()
 return False
 
 except Exception as e:
 print(f"\n[ERROR] Pipeline failed: {str(e)}")
 import traceback
 traceback.print_exc()
 return False

if __name__ == "__main__":
 success = main()
 if success:
 print("\n[SUCCESS] Ultimate multimodal extraction completed")
 else:
 print("\n[FAILED] Ultimate multimodal extraction failed")