#!/usr/bin/env python3
import json
import glob

# Find all AutoSchemaKG JSON files
json_files = glob.glob("autoschema_database_output/kg_output/kg_extraction/*.json")
print(f"Found {len(json_files)} AutoSchemaKG JSON files")

if json_files:
 # Load first file as sample
 with open(json_files[0], 'r', encoding='utf-8', errors='ignore') as f:
 content = f.read()
 data = json.loads(content)
 
 print(f"\nAnalyzing: {json_files[0]}")
 print(f"Total documents in file: {len(data)}")
 
 # Check first document structure
 if data:
 first_doc_key = list(data.keys())[0]
 first_doc = data[first_doc_key]
 
 print(f"\nFirst document: {first_doc_key[:50]}...")
 print(f"Keys in document: {list(first_doc.keys())}")
 
 # Check entities
 entities = first_doc.get('entities', [])
 print(f"\nTotal entities: {len(entities)}")
 
 # Look for visual-related entities
 visual_entities = []
 for e in entities:
 entity_str = str(e).lower()
 if any(word in entity_str for word in ['image', 'figure', 'diagram', '.png', '.jpg', 'visual', 'illustration']):
 visual_entities.append(e)
 
 print(f"Visual-related entities found: {len(visual_entities)}")
 for ve in visual_entities[:5]:
 print(f" - {ve.get('entity_name', 'N/A')[:60]} ({ve.get('entity_type', 'N/A')})")
 
 # Check relationships
 relationships = first_doc.get('relationships', [])
 print(f"\nTotal relationships: {len(relationships)}")
 
 # Look for visual-related relationships
 visual_rels = []
 for r in relationships:
 rel_str = str(r).lower()
 if any(word in rel_str for word in ['image', 'figure', 'diagram', '.png', '.jpg', 'visual', 'illustration']):
 visual_rels.append(r)
 
 print(f"Visual-related relationships found: {len(visual_rels)}")
 for vr in visual_rels[:5]:
 print(f" - {vr.get('head', 'N/A')[:30]} --[{vr.get('relation', 'N/A')}]--> {vr.get('tail', 'N/A')[:30]}")