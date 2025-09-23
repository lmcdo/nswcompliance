#!/usr/bin/env python3
"""
Import Zone Data from AutoSchemaKG to SQLite
===========================================
Extract NSW zone definitions and populate the zone column in regulatory_provisions
"""

import json
import sqlite3
import re

def import_zones_from_autoschema():
 print("IMPORTING ZONES FROM AUTOSCHEMAKG TO SQLITE")
 print("=" * 60)
 
 # Read AutoSchemaKG file line by line (JSONL format)
 zone_mappings = {}
 try:
 with open('autoschemakg_output_ollama_final/kg_extraction/llama3.1_8b_nsw_planning_docs_output_20250829000809_1_in_1.json', 'r', encoding='utf-8') as f:
 content = f.read()
 # Split on newlines and parse each JSON object
 for line_num, line in enumerate(content.split('\n')):
 if line.strip():
 try:
 record = json.loads(line)
 
 # Look for zone entities in event_entity_relation_dict
 if 'event_entity_relation_dict' in record:
 for event in record['event_entity_relation_dict']:
 event_text = event.get('Event', '')
 entities = event.get('Entity', [])
 
 # Extract zone codes (R1, R2, B1, etc.)
 if 'Zone' in event_text:
 zone_matches = re.findall(r'Zone ([A-Z]+\d+[A-Z]*)', event_text)
 for zone_match in zone_matches:
 zone_mappings[zone_match] = {
 'document': record.get('metadata', {}).get('document_name', ''),
 'description': event_text
 }
 
 # Also check entities for zone references 
 for entity in entities:
 if isinstance(entity, str) and 'Zone' in entity:
 zone_matches = re.findall(r'Zone ([A-Z]+\d+[A-Z]*)', entity)
 for zone_match in zone_matches:
 zone_mappings[zone_match] = {
 'document': record.get('metadata', {}).get('document_name', ''),
 'description': entity
 }
 
 # Also check original_text for zone definitions
 original_text = record.get('original_text', '')
 if 'Zone' in original_text:
 zone_matches = re.findall(r'Zone ([A-Z]+\d+[A-Z]*)', original_text)
 for zone_match in zone_matches:
 zone_mappings[zone_match] = {
 'document': record.get('metadata', {}).get('document_name', ''),
 'description': f'Found in {record.get("metadata", {}).get("document_name", "")}'
 }
 
 except json.JSONDecodeError:
 continue # Skip malformed JSON lines
 
 except Exception as e:
 print(f"Error reading AutoSchemaKG file: {e}")
 return 0
 
 print(f"Extracted {len(zone_mappings)} unique zone codes:")
 for zone, info in sorted(zone_mappings.items()):
 print(f" {zone}: {info['description'][:100]}...")
 
 # Connect to database and update zone fields
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 updates_made = 0
 
 try:
 # Update regulatory_provisions with zone information based on document content
 for zone_code, zone_info in zone_mappings.items():
 document_pattern = zone_info['document'].replace('.pdf', '').replace('_', ' ')
 
 # Update provisions that mention this zone in their text
 cursor.execute("""
 UPDATE regulatory_provisions 
 SET zone = ?
 WHERE (provision_text LIKE ? OR provision_text LIKE ? OR document_id LIKE ?)
 AND (zone IS NULL OR zone = '')
 """, (
 zone_code,
 f'%Zone {zone_code}%',
 f'%{zone_code} %',
 f'%{document_pattern}%'
 ))
 
 rows_updated = cursor.rowcount
 if rows_updated > 0:
 print(f"Updated {rows_updated} provisions with zone {zone_code}")
 updates_made += rows_updated
 
 # Also try to infer zones from document names
 cursor.execute("""
 SELECT DISTINCT document_id FROM regulatory_provisions 
 WHERE (zone IS NULL OR zone = '') 
 AND document_id IS NOT NULL
 """)
 
 documents = cursor.fetchall()
 for (doc_id,) in documents:
 # Try to extract zone from document ID
 doc_zones = re.findall(r'([A-Z]+\d+[A-Z]*)', doc_id.upper())
 
 # Filter to valid NSW zone patterns
 valid_zones = [z for z in doc_zones if re.match(r'^(R[1-5]|B[1-8]|IN[1-4]|E[1-5]|SP[1-5]|RU[1-6]|RE[1-2]|W[1-4]|C[1-4])$', z)]
 
 if valid_zones:
 primary_zone = valid_zones[0] # Use first valid zone found
 cursor.execute("""
 UPDATE regulatory_provisions 
 SET zone = ?
 WHERE document_id = ? AND (zone IS NULL OR zone = '')
 """, (primary_zone, doc_id))
 
 rows_updated = cursor.rowcount
 if rows_updated > 0:
 print(f"Updated {rows_updated} provisions with zone {primary_zone} from document {doc_id}")
 updates_made += rows_updated
 
 conn.commit()
 
 # Verify results
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''")
 zone_count = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
 total_count = cursor.fetchone()[0]
 
 print(f"\nZONE IMPORT COMPLETE:")
 print(f" Records with zones: {zone_count}/{total_count} ({zone_count/total_count*100:.1f}%)")
 print(f" Updates made: {updates_made}")
 
 return updates_made
 
 except Exception as e:
 print(f"Database error: {e}")
 conn.rollback()
 return 0
 finally:
 conn.close()

if __name__ == "__main__":
 import_zones_from_autoschema()