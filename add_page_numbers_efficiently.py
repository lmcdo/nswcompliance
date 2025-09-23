#!/usr/bin/env python3
"""
Efficiently Add Page Numbers & TOC to Existing Database
=====================================================
Maps existing regulatory_refs entries to RAG-Anything page numbers without rerunning extraction
"""

import sqlite3
import json
from difflib import SequenceMatcher
import re

def similarity(a, b):
 """Calculate text similarity for matching"""
 return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_text(text):
 """Normalize text for better matching"""
 if not text:
 return ""
 # Remove extra whitespace, normalize punctuation
 text = re.sub(r'\s+', ' ', text.strip())
 text = re.sub(r'[^\w\s\.]', '', text)
 return text.lower()

def add_page_number_columns():
 """Add page number columns to database"""
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 try:
 cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN page_number INTEGER")
 cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN section_header TEXT")
 cursor.execute("ALTER TABLE regulatory_refs ADD COLUMN text_level INTEGER")
 print("[OK] Added page number columns to database")
 except sqlite3.OperationalError as e:
 if "duplicate column name" in str(e):
 print("[OK] Page number columns already exist")
 else:
 raise
 
 conn.commit()
 conn.close()

def build_raganything_content_index():
 """Build searchable index from RAG-Anything data"""
 print("Loading RAG-Anything structured content...")
 
 try:
 with open('multimodal_relationships_complete.json', 'r', encoding='utf-8') as f:
 rag_data = json.load(f)
 except Exception as e:
 print(f"[ERROR] Error loading RAG-Anything data: {e}")
 return {}
 
 content_index = {}
 doc_count = 0
 
 for doc_name, doc_data in rag_data.get('documents', {}).items():
 current_section = "Introduction"
 section_hierarchy = []
 
 for item in doc_data.get('content_sequence', []):
 text = item.get('text', '').strip()
 if not text or len(text) < 10: # Skip very short content
 continue
 
 text_level = item.get('text_level', 0)
 page_idx = item.get('page_idx', 0)
 
 # Track section hierarchy
 if text_level == 1:
 current_section = text[:100] # Truncate long headers
 section_hierarchy = [current_section]
 elif text_level == 2 and len(section_hierarchy) >= 1:
 if len(section_hierarchy) > 1:
 section_hierarchy[1] = text[:100]
 else:
 section_hierarchy.append(text[:100])
 
 # Create multiple search keys for better matching
 normalized_text = normalize_text(text)
 
 # Store with multiple access patterns
 content_index[normalized_text] = {
 'page': page_idx,
 'section': current_section,
 'text_level': text_level,
 'doc_name': doc_name,
 'hierarchy': section_hierarchy.copy(),
 'original_text': text
 }
 
 # Also index by key phrases (first 50 chars)
 if len(text) > 50:
 key_phrase = normalize_text(text[:50])
 if key_phrase not in content_index:
 content_index[key_phrase] = content_index[normalized_text]
 
 doc_count += 1
 
 print(f"[OK] Indexed {len(content_index):,} content items from {doc_count} documents")
 return content_index

def find_best_page_match(db_context, content_index):
 """Find best matching page number for database entry"""
 if not db_context:
 return None
 
 normalized_context = normalize_text(db_context)
 
 # Direct match first
 if normalized_context in content_index:
 return content_index[normalized_context]
 
 # Similarity matching for partial matches
 best_match = None
 best_score = 0.0
 
 search_phrase = normalized_context[:100] # Use first 100 chars for matching
 
 for content_text, content_data in content_index.items():
 if len(content_text) < 10: # Skip short content
 continue
 
 # Calculate similarity
 score = similarity(search_phrase, content_text[:100])
 
 # Boost for exact clause number matches
 if any(char.isdigit() for char in search_phrase):
 # Extract numbers from both texts
 db_numbers = set(re.findall(r'\d+\.?\d*', search_phrase))
 content_numbers = set(re.findall(r'\d+\.?\d*', content_text))
 if db_numbers & content_numbers: # Common numbers
 score += 0.2
 
 if score > best_score and score > 0.5: # Minimum threshold
 best_score = score
 best_match = content_data.copy()
 best_match['match_score'] = score
 
 return best_match if best_score > 0.6 else None

def process_page_number_mapping():
 """Map existing database entries to page numbers"""
 print("Mapping database entries to page numbers...")
 
 # Build RAG-Anything index
 content_index = build_raganything_content_index()
 if not content_index:
 print("[ERROR] No content index available")
 return 0
 
 # Process database entries
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get all entries without page numbers
 cursor.execute("""
 SELECT id, document_id, ref_context 
 FROM regulatory_refs 
 WHERE page_number IS NULL
 LIMIT 1000
 """) # Process in batches for memory efficiency
 
 entries = cursor.fetchall()
 print(f"Processing {len(entries)} database entries...")
 
 matches_found = 0
 processed = 0
 
 for entry_id, document_id, ref_context in entries:
 processed += 1
 
 if processed % 100 == 0:
 print(f" Progress: {processed}/{len(entries)} ({processed/len(entries)*100:.1f}%)")
 
 # Find best page match
 page_match = find_best_page_match(ref_context, content_index)
 
 if page_match:
 # Update database entry
 cursor.execute("""
 UPDATE regulatory_refs 
 SET page_number = ?, section_header = ?, text_level = ?
 WHERE id = ?
 """, (
 page_match['page'],
 page_match['section'],
 page_match.get('text_level', 0),
 entry_id
 ))
 matches_found += 1
 
 conn.commit()
 
 # Get final stats
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL")
 total_with_pages = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_entries = cursor.fetchone()[0]
 
 conn.close()
 
 print(f"\n[OK] PAGE NUMBER MAPPING COMPLETE")
 print(f" Entries processed: {processed:,}")
 print(f" Matches found: {matches_found:,}")
 print(f" Success rate: {matches_found/processed*100:.1f}%")
 print(f" Total with pages: {total_with_pages:,}/{total_entries:,} ({total_with_pages/total_entries*100:.1f}%)")
 
 return matches_found

def create_sample_queries():
 """Show sample queries with page numbers"""
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 print("\nSAMPLE QUERIES WITH PAGE NUMBERS:")
 
 cursor.execute("""
 SELECT ref_type, ref_context, page_number, section_header
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL
 ORDER BY page_number
 LIMIT 5
 """)
 
 for ref_type, context, page_num, section in cursor.fetchall():
 print(f"\n [Page {page_num}] {section}")
 print(f" Type: {ref_type}")
 print(f" Rule: {context[:80]}...")
 
 conn.close()

if __name__ == "__main__":
 print("EFFICIENT PAGE NUMBER INTEGRATION")
 print("=" * 50)
 
 # Step 1: Add database columns
 add_page_number_columns()
 
 # Step 2: Map existing entries to page numbers 
 matches = process_page_number_mapping()
 
 if matches > 0:
 print(f"\n[SUCCESS] Added page numbers to {matches:,} entries")
 create_sample_queries()
 else:
 print("\n[WARNING] No page number matches found - check RAG-Anything data")