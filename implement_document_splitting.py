#!/usr/bin/env python3
"""
Implement Document Splitting for Large PDFs
===========================================
Splits large documents into manageable sections to prevent pipeline stalls
"""

import sqlite3
import re
from datetime import datetime

def split_large_document(pdf_name, full_text, max_chars=250000):
 """Split a document into sections based on natural breaks"""
 
 # Define section patterns for different document types
 section_patterns = {
 'SEPP': [
 r'^(Division \d+.*?)$',
 r'^(Part \d+.*?)$', 
 r'^(Chapter \d+.*?)$',
 r'^(Schedule \d+.*?)$',
 r'^(Clause \d+.*?)$'
 ],
 'DCP': [
 r'^(Section \d+\.\d+.*?)$',
 r'^(\d+\.\d+\.\d+.*?)$',
 r'^(PART [IVX]+.*?)$',
 r'^([A-Z][A-Z\s]+ PRECINCT.*?)$'
 ],
 'LEP': [
 r'^(Part \d+.*?)$',
 r'^(Division \d+.*?)$', 
 r'^(Schedule \d+.*?)$',
 r'^(Clause \d+.*?)$'
 ]
 }
 
 # Determine document type
 doc_type = 'DCP' # Default
 if 'Environmental Planning Policy' in pdf_name:
 doc_type = 'SEPP'
 elif 'Local Environmental Plan' in pdf_name:
 doc_type = 'LEP'
 
 print(f"Splitting {pdf_name} (Type: {doc_type}, {len(full_text):,} chars)")
 
 # Split into lines for analysis
 lines = full_text.split('\n')
 sections = []
 current_section_start = 0
 current_section_lines = []
 section_count = 0
 
 patterns = section_patterns.get(doc_type, section_patterns['DCP'])
 
 for i, line in enumerate(lines):
 line_stripped = line.strip()
 
 # Check if this line starts a new section
 is_section_start = False
 for pattern in patterns:
 if re.match(pattern, line_stripped, re.IGNORECASE):
 is_section_start = True
 break
 
 if is_section_start and len(current_section_lines) > 100: # Don't split tiny sections
 # Save current section
 section_text = '\n'.join(current_section_lines)
 if len(section_text) > 5000: # Only save substantial sections
 sections.append({
 'section_id': section_count,
 'title': current_section_lines[0][:100] if current_section_lines else f'Section {section_count}',
 'text': section_text,
 'char_count': len(section_text),
 'line_start': current_section_start,
 'line_end': i
 })
 section_count += 1
 
 # Start new section
 current_section_start = i
 current_section_lines = [line]
 else:
 current_section_lines.append(line)
 
 # Add final section
 if current_section_lines:
 section_text = '\n'.join(current_section_lines)
 if len(section_text) > 5000:
 sections.append({
 'section_id': section_count,
 'title': current_section_lines[0][:100] if current_section_lines else f'Final Section',
 'text': section_text,
 'char_count': len(section_text),
 'line_start': current_section_start,
 'line_end': len(lines)
 })
 
 print(f" Split into {len(sections)} sections")
 for section in sections:
 print(f" Section {section['section_id']}: {section['char_count']:,} chars - {section['title']}")
 
 return sections

def create_split_documents():
 """Create split versions of large documents in database"""
 
 # Target large documents for splitting
 large_doc_patterns = [
 "State Environmental Planning Policy (Exempt and Complying Development Codes)",
 "Inner West Local Environmental Plan 2022",
 "Marrickville DCP 2011 - 8.0 Heritage",
 "State Environmental Planning Policy (Housing) 2021"
 ]
 
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 print("IMPLEMENTING DOCUMENT SPLITTING")
 print("=" * 50)
 
 splits_created = 0
 
 for pattern in large_doc_patterns:
 # Find matching document
 cursor.execute("""
 SELECT id, pdf_name, full_text, char_count
 FROM documents 
 WHERE pdf_name LIKE ? AND char_count > 250000
 """, (f'%{pattern}%',))
 
 matches = cursor.fetchall()
 
 for doc_id, pdf_name, full_text, char_count in matches:
 print(f"\nProcessing: {pdf_name}")
 print(f"Original size: {char_count:,} characters")
 
 # Split the document
 sections = split_large_document(pdf_name, full_text)
 
 if len(sections) > 1:
 # Create split documents
 for section in sections:
 split_id = f"{doc_id}_section_{section['section_id']}"
 split_name = f"{pdf_name.replace('.pdf', '')} - Section {section['section_id']}.pdf"
 
 # Insert split document (get pdf_path from original) 
 cursor.execute("SELECT pdf_path FROM documents WHERE id = ?", (doc_id,))
 path_result = cursor.fetchone()
 original_path = path_result[0] if path_result else 'virtual_split'
 
 cursor.execute("""
 INSERT OR REPLACE INTO documents 
 (id, pdf_name, document_type, pdf_path, full_text, char_count, word_count, extraction_timestamp)
 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
 """, (
 split_id,
 split_name,
 'SEPP' if 'Environmental Planning Policy' in pdf_name else 'DCP',
 f"{original_path}_section_{section['section_id']}",
 section['text'],
 section['char_count'],
 len(section['text'].split()),
 datetime.now().timestamp()
 ))
 
 splits_created += 1
 print(f" Created: {split_name} ({section['char_count']:,} chars)")
 
 # Add note to original document name to indicate it was split
 cursor.execute("""
 UPDATE documents 
 SET pdf_name = ?
 WHERE id = ?
 """, (f"{pdf_name.replace('.pdf', '')} - [SPLIT INTO {len(sections)} SECTIONS].pdf", doc_id))
 
 else:
 print(f" Could not split effectively - keeping original")
 
 # No need to add new columns - using existing schema
 
 conn.commit()
 conn.close()
 
 print(f"\nSUMMARY")
 print(f" Split documents created: {splits_created}")
 print(f" Large documents processed: {len(large_doc_patterns)}")
 
 return splits_created

def update_resume_config_with_splits():
 """Update resume config to use split documents instead of large ones"""
 
 import json
 
 # Read current config
 with open('resume_config.json', 'r') as f:
 config = json.load(f)
 
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Get all split sections (identify by naming pattern)
 cursor.execute("""
 SELECT pdf_name, id
 FROM documents 
 WHERE pdf_name LIKE '% - Section %.pdf'
 ORDER BY pdf_name
 """)
 
 split_sections = cursor.fetchall()
 
 # Get parent document names (identify by "[SPLIT INTO X SECTIONS]" marker)
 cursor.execute("""
 SELECT pdf_name, id
 FROM documents 
 WHERE pdf_name LIKE '%[SPLIT INTO%SECTIONS].pdf'
 """)
 
 parent_docs = cursor.fetchall()
 parent_mapping = {}
 
 for parent_name, parent_id in parent_docs:
 # Extract original name
 original_name = parent_name.split(' - [SPLIT INTO')[0] + '.pdf'
 parent_mapping[original_name] = parent_name
 
 conn.close()
 
 # Update config - replace large docs with their splits
 updated_docs = []
 replaced_count = 0
 
 for doc in config['remaining_documents']:
 # Check if this doc was split
 if doc in parent_mapping:
 # Replace with split sections
 doc_base = doc.replace('.pdf', '')
 for split_name, split_id in split_sections:
 if split_name.startswith(doc_base + ' - Section'):
 updated_docs.append(split_name)
 replaced_count += 1
 print(f"Replaced {doc} with {len([s for s, _ in split_sections if s.startswith(doc_base)])} sections")
 else:
 updated_docs.append(doc)
 
 # Update config
 config['remaining_documents'] = updated_docs
 config['split_processing_applied'] = True
 config['replaced_large_docs'] = replaced_count
 config['split_update_time'] = datetime.now().isoformat()
 
 # Save updated config
 with open('resume_config_with_splits.json', 'w') as f:
 json.dump(config, f, indent=2)
 
 print(f"\nUPDATED RESUME CONFIGURATION")
 print(f" Original documents: {len(config['remaining_documents']) - len(updated_docs) + replaced_count}")
 print(f" Updated documents: {len(updated_docs)}")
 print(f" Large docs replaced: {replaced_count}")
 print(f" Configuration saved to: resume_config_with_splits.json")
 
 return len(updated_docs), replaced_count

if __name__ == "__main__":
 splits_created = create_split_documents()
 if splits_created > 0:
 update_resume_config_with_splits()
 print("\nDocument splitting complete! Use resume_config_with_splits.json for processing.")
 else:
 print("\nNo splits created - documents may already be processed or not found.")