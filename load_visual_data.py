#!/usr/bin/env python3
"""
Load visual data from multimodal_relationships_complete.json into database
This was missing from the original migration!
"""

import json
import sqlite3
from pathlib import Path

def load_visual_data():
 print("LOADING VISUAL DATA INTO DATABASE")
 print("=" * 60)
 
 # Connect to database
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Load multimodal data
 multimodal_file = 'multimodal_relationships_complete.json'
 if not Path(multimodal_file).exists():
 print(f"ERROR: {multimodal_file} not found!")
 return
 
 print(f"Loading {multimodal_file}...")
 with open(multimodal_file, 'r', encoding='utf-8', errors='ignore') as f:
 # Read line by line and parse carefully
 content = f.read()
 # Try to fix common JSON issues
 content = content.replace(',\n}', '\n}').replace(',\n]', '\n]')
 try:
 data = json.loads(content)
 except json.JSONDecodeError as e:
 print(f"JSON Error: {e}")
 print("Attempting to parse as much as possible...")
 # Try to parse up to the error point
 try:
 partial_content = content[:e.pos]
 # Close any open brackets
 open_braces = partial_content.count('{') - partial_content.count('}')
 open_brackets = partial_content.count('[') - partial_content.count(']')
 partial_content += ']' * open_brackets + '}' * open_braces
 data = json.loads(partial_content)
 except:
 print("Failed to parse JSON. Exiting.")
 return
 
 documents = data.get('documents', {})
 print(f"Found {len(documents)} documents with visual content")
 
 visual_count = 0
 text_visual_links = []
 
 for doc_name, doc_data in documents.items():
 content_seq = doc_data.get('content_sequence', [])
 
 # Track the last text provision for linking
 last_text_provision_id = None
 
 for idx, item in enumerate(content_seq):
 if item['type'] == 'text':
 # Find or create a provision for this text
 text = item.get('text', '')
 page = item.get('page_idx', 0)
 level = item.get('text_level', 0)
 
 # Check if provision exists
 cur.execute("""
 SELECT id FROM regulatory_provisions 
 WHERE document_id = ? AND provision_text = ? AND page_number = ?
 LIMIT 1
 """, (doc_name, text[:500], page)) # Truncate text for matching
 
 result = cur.fetchone()
 if result:
 last_text_provision_id = result[0]
 
 elif item['type'] == 'image':
 # Insert visual element
 img_path = item.get('img_path', '')
 caption = ' '.join(item.get('image_caption', []))
 footnote = ' '.join(item.get('image_footnote', []))
 page = item.get('page_idx', 0)
 
 # Determine visual type from path or caption
 visual_type = 'image'
 if 'diagram' in caption.lower() or 'diagram' in img_path.lower():
 visual_type = 'diagram'
 elif 'figure' in caption.lower() or 'fig' in caption.lower():
 visual_type = 'figure'
 elif 'table' in caption.lower():
 visual_type = 'table'
 
 # Insert into visual_elements table
 cur.execute("""
 INSERT INTO visual_elements 
 (provision_id, visual_type, visual_path, visual_description, page_number, autoschema_source)
 VALUES (?, ?, ?, ?, ?, ?)
 """, (last_text_provision_id, visual_type, img_path, caption + ' ' + footnote, page, True))
 
 visual_count += 1
 
 if visual_count % 100 == 0:
 print(f" Loaded {visual_count} visual elements...")
 
 conn.commit()
 
 print(f"\nSUCCESS: Loaded {visual_count} visual elements into database")
 
 # Verify the data was loaded
 count = cur.execute("SELECT COUNT(*) FROM visual_elements").fetchone()[0]
 print(f"Database now contains {count} visual elements")
 
 # Show sample
 samples = cur.execute("""
 SELECT visual_type, visual_path, visual_description 
 FROM visual_elements 
 LIMIT 5
 """).fetchall()
 
 print("\nSample visual elements:")
 for vtype, path, desc in samples:
 print(f" {vtype}: {path[:50]}... - {desc[:50]}...")
 
 conn.close()
 print("\nVisual data loading complete!")

if __name__ == "__main__":
 load_visual_data()