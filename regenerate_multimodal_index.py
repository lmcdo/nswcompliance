#!/usr/bin/env python3
"""
Regenerate multimodal relationships from all RAG-Anything outputs
"""

import json
import os
from pathlib import Path

def regenerate_multimodal_index():
 """Scan all RAG-Anything outputs and rebuild multimodal index"""
 
 print("REGENERATING MULTIMODAL INDEX")
 print("=" * 50)
 
 output_dir = Path("output")
 multimodal_data = {"documents": {}}
 
 total_images = 0
 total_text = 0
 total_tables = 0
 
 # Process each document directory
 for doc_dir in output_dir.iterdir():
 if not doc_dir.is_dir():
 continue
 
 # Look for content_list.json files
 auto_dir = doc_dir / "auto"
 if not auto_dir.exists():
 continue
 
 # Find content_list.json
 content_files = list(auto_dir.glob("*_content_list.json"))
 
 for content_file in content_files:
 print(f"Processing: {doc_dir.name}")
 
 try:
 with open(content_file, 'r', encoding='utf-8') as f:
 content_data = json.load(f)
 
 # Count elements
 doc_images = 0
 doc_text = 0
 doc_tables = 0
 
 for item in content_data:
 if item.get("type") == "image":
 doc_images += 1
 total_images += 1
 elif item.get("type") == "text":
 doc_text += 1
 total_text += 1
 elif item.get("type") == "table":
 doc_tables += 1
 total_tables += 1
 
 # Store document data
 multimodal_data["documents"][doc_dir.name] = {
 "document_name": doc_dir.name,
 "content_sequence": content_data,
 "statistics": {
 "images": doc_images,
 "text_sections": doc_text,
 "tables": doc_tables
 }
 }
 
 print(f" - Images: {doc_images}, Text: {doc_text}, Tables: {doc_tables}")
 
 except Exception as e:
 print(f" ERROR: {e}")
 
 # Save regenerated data
 output_file = "multimodal_relationships_complete.json"
 with open(output_file, 'w', encoding='utf-8') as f:
 json.dump(multimodal_data, f, indent=2)
 
 print(f"\nREGENERATION COMPLETE")
 print(f" Documents: {len(multimodal_data['documents'])}")
 print(f" Total images: {total_images}")
 print(f" Total text sections: {total_text}")
 print(f" Total tables: {total_tables}")
 print(f" Output: {output_file}")
 
 # Create AutoSchema input
 autoschema_input = {
 "entities": [],
 "relationships": []
 }
 
 for doc_idx, (doc_name, doc_data) in enumerate(multimodal_data["documents"].items()):
 # Create document entity
 autoschema_input["entities"].append({
 "id": f"doc_{doc_idx}",
 "type": "document",
 "name": doc_name,
 "attributes": doc_data["statistics"]
 })
 
 # Create entities for images with clause context
 for item_idx, item in enumerate(doc_data["content_sequence"]):
 if item.get("type") == "image":
 # Find surrounding clause context
 clause_context = find_clause_context(doc_data["content_sequence"], item_idx)
 
 autoschema_input["entities"].append({
 "id": f"img_{doc_idx}_{item_idx}",
 "type": "image",
 "path": item.get("img_path", ""),
 "page": item.get("page_idx", 0),
 "clause_context": clause_context,
 "document": doc_name
 })
 
 # Create relationship
 if clause_context:
 autoschema_input["relationships"].append({
 "source": f"img_{doc_idx}_{item_idx}",
 "target": f"doc_{doc_idx}",
 "type": "illustrates_clause",
 "clause": clause_context
 })
 
 # Save AutoSchema input
 autoschema_file = "autoschema_multimodal_complete.json"
 with open(autoschema_file, 'w', encoding='utf-8') as f:
 json.dump(autoschema_input, f, indent=2)
 
 print(f"\nAutoSchema input created:")
 print(f" Entities: {len(autoschema_input['entities'])}")
 print(f" Relationships: {len(autoschema_input['relationships'])}")
 print(f" Output: {autoschema_file}")


def find_clause_context(sequence, image_idx, context_range=5):
 """Find clause references near an image - FIXED for NSW planning patterns"""
 import re
 
 # Search before and after image
 start_idx = max(0, image_idx - context_range)
 end_idx = min(len(sequence), image_idx + context_range)
 
 for i in range(start_idx, end_idx):
 if sequence[i].get("type") == "text":
 text = sequence[i].get("text", "").strip()
 
 # COMPREHENSIVE NSW planning clause patterns
 patterns = [
 r'^C(\d+)$', # C16, C1, etc. (Control clauses)
 r'^P(\d+)$', # P1, P2, etc. (Performance outcomes)
 r'^DS(\d+(?:\.\d+)*)$', # DS1.1, DS3.6, etc. (Design solutions)
 r'^PC-(\d+)$', # PC-12, PC-15, etc. (Precinct controls)
 r'(?:clause|section)\s+(\d+(?:\.\d+)*)', # Traditional "Clause 4.2.4"
 r'^(\d+\.\d+\.\d+)$', # 4.2.4 format (section numbers)
 r'^(\d+\.\d+)$', # 9.1 format (major sections)
 ]
 
 for pattern in patterns:
 match = re.search(pattern, text, re.IGNORECASE)
 if match:
 # Return properly formatted clause reference
 if pattern.startswith('^C'):
 return f'C{match.group(1)}'
 elif pattern.startswith('^P'): 
 return f'P{match.group(1)}'
 elif pattern.startswith('^DS'):
 return f'DS{match.group(1)}'
 elif pattern.startswith('^PC'):
 return f'PC-{match.group(1)}'
 else:
 return match.group(1)
 
 return None


if __name__ == "__main__":
 regenerate_multimodal_index()