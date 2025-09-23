#!/usr/bin/env python3
"""
Fast Page Number Integration - Optimized Version
==============================================
"""

import sqlite3
import json
from difflib import SequenceMatcher
import re

def similarity(a, b):
 """Fast similarity calculation"""
 return SequenceMatcher(None, a[:100].lower(), b[:100].lower()).ratio()

def process_page_mapping_fast():
 """Fast version - process first 100 entries to test"""
 print("FAST PAGE NUMBER INTEGRATION")
 print("=" * 40)
 
 # Load RAG-Anything data
 print("Loading RAG-Anything content...")
 try:
 with open('multimodal_relationships_complete.json', 'r', encoding='utf-8') as f:
 rag_data = json.load(f)
 print(f"[OK] Loaded {len(rag_data['documents'])} documents")
 except Exception as e:
 print(f"[ERROR] {e}")
 return
 
 # Build simple content map
 content_map = {}
 total_items = 0
 
 for doc_name, doc_data in rag_data['documents'].items():
 current_section = "Introduction"
 
 for item in doc_data.get('content_sequence', []):
 if item.get('type') == 'text':
 text = item.get('text', '').strip()
 if len(text) > 30: # Only substantial text
 
 # Track section headers
 if item.get('text_level') == 1:
 current_section = text[:80]
 
 # Create search key
 search_key = text[:100].lower().strip()
 content_map[search_key] = {
 'page': item.get('page_idx', 0),
 'section': current_section,
 'level': item.get('text_level', 0)
 }
 total_items += 1
 
 print(f"[OK] Indexed {total_items:,} content items for matching")
 
 # Process database entries
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get first 100 entries for testing
 cursor.execute("""
 SELECT id, ref_context 
 FROM regulatory_refs 
 WHERE page_number IS NULL
 LIMIT 100
 """)
 entries = cursor.fetchall()
 print(f"Processing {len(entries)} test entries...")
 
 matches = 0
 for entry_id, context in entries:
 if not context:
 continue
 
 search_text = context[:100].lower().strip()
 
 # Direct match first
 if search_text in content_map:
 page_data = content_map[search_text]
 cursor.execute("""
 UPDATE regulatory_refs 
 SET page_number = ?, section_header = ?, text_level = ?
 WHERE id = ?
 """, (page_data['page'], page_data['section'], page_data['level'], entry_id))
 matches += 1
 continue
 
 # Similarity match
 best_score = 0
 best_match = None
 
 for content_key, page_data in list(content_map.items())[:1000]: # Limit search
 score = similarity(search_text, content_key)
 if score > best_score and score > 0.7:
 best_score = score
 best_match = page_data
 
 if best_match:
 cursor.execute("""
 UPDATE regulatory_refs 
 SET page_number = ?, section_header = ?, text_level = ?
 WHERE id = ?
 """, (best_match['page'], best_match['section'], best_match['level'], entry_id))
 matches += 1
 
 conn.commit()
 
 # Check results
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL")
 total_with_pages = cursor.fetchone()[0]
 
 # Show samples
 cursor.execute("""
 SELECT ref_context, page_number, section_header
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL
 LIMIT 5
 """)
 samples = cursor.fetchall()
 
 conn.close()
 
 print(f"\nRESULTS:")
 print(f" Test entries processed: {len(entries)}")
 print(f" Matches found: {matches}")
 print(f" Success rate: {matches/len(entries)*100:.1f}%")
 print(f" Total with pages: {total_with_pages:,}")
 
 if samples:
 print(f"\nSAMPLE RESULTS:")
 for context, page, section in samples:
 print(f" Page {page} | {section[:40]}...")
 print(f" Rule: {context[:60]}...")

if __name__ == "__main__":
 process_page_mapping_fast()