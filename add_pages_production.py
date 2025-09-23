#!/usr/bin/env python3
"""
Production Page Number Integration - Full Scale
=============================================
Process all 7,400+ entries with proven 48% success rate
"""

import sqlite3
import json
from difflib import SequenceMatcher

def similarity(a, b):
 """Fast similarity calculation"""
 return SequenceMatcher(None, a[:100].lower(), b[:100].lower()).ratio()

def process_all_page_mapping():
 """Production version - process all entries in batches"""
 print("PRODUCTION PAGE NUMBER INTEGRATION")
 print("=" * 50)
 print("Expected: 48% success rate = ~3,500 entries get page numbers")
 print()
 
 # Load RAG-Anything data
 print("Loading RAG-Anything content...")
 try:
 with open('multimodal_relationships_complete.json', 'r', encoding='utf-8') as f:
 rag_data = json.load(f)
 print(f"[OK] Loaded {len(rag_data['documents'])} documents")
 except Exception as e:
 print(f"[ERROR] {e}")
 return
 
 # Build content map (optimized)
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
 
 print(f"[OK] Indexed {total_items:,} content items")
 
 # Process all database entries in batches
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get total count
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NULL")
 total_to_process = cursor.fetchone()[0]
 print(f"Processing {total_to_process:,} database entries...")
 
 batch_size = 500
 matches_total = 0
 processed_total = 0
 
 for offset in range(0, total_to_process, batch_size):
 # Get batch
 cursor.execute("""
 SELECT id, ref_context 
 FROM regulatory_refs 
 WHERE page_number IS NULL
 LIMIT ? OFFSET ?
 """, (batch_size, offset))
 
 entries = cursor.fetchall()
 if not entries:
 break
 
 batch_matches = 0
 
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
 batch_matches += 1
 continue
 
 # Quick similarity match (limited search for performance)
 best_score = 0
 best_match = None
 
 # Search subset for performance
 search_count = 0
 for content_key, page_data in content_map.items():
 search_count += 1
 if search_count > 2000: # Limit search to keep it fast
 break
 
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
 batch_matches += 1
 
 # Commit batch
 conn.commit()
 
 # Update totals
 matches_total += batch_matches
 processed_total += len(entries)
 
 # Progress report
 progress = processed_total / total_to_process * 100
 success_rate = batch_matches / len(entries) * 100 if entries else 0
 
 print(f" Batch {offset//batch_size + 1}: {batch_matches}/{len(entries)} matches ({success_rate:.1f}%) | Progress: {progress:.1f}%")
 
 # Final results
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs WHERE page_number IS NOT NULL")
 total_with_pages = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(*) FROM regulatory_refs")
 total_entries = cursor.fetchone()[0]
 
 # Sample results
 cursor.execute("""
 SELECT ref_context, page_number, section_header, text_level
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL
 ORDER BY page_number
 LIMIT 8
 """)
 samples = cursor.fetchall()
 
 conn.close()
 
 print(f"\nPRODUCTION RESULTS:")
 print(f"=" * 30)
 print(f" Total processed: {processed_total:,}")
 print(f" Matches found: {matches_total:,}")
 print(f" Overall success rate: {matches_total/processed_total*100:.1f}%")
 print(f" Database coverage: {total_with_pages:,}/{total_entries:,} ({total_with_pages/total_entries*100:.1f}%)")
 
 if samples:
 print(f"\nSAMPLE RESULTS WITH PAGE NUMBERS:")
 for context, page, section, level in samples:
 print(f" Page {page:2} Level {level} | {section[:50]}...")
 print(f" Rule: {context[:70]}...")
 print()

if __name__ == "__main__":
 process_all_page_mapping()