#!/usr/bin/env python3
"""
Comprehensive Zone Extractor from All JSON Sources
================================================
Extract ALL zone relationships and setback data from JSON files
"""

import json
import sqlite3
import re
import os
from pathlib import Path

def extract_zones_from_all_sources():
 print("COMPREHENSIVE ZONE EXTRACTION FROM ALL JSON SOURCES")
 print("=" * 60)
 
 zone_provisions = {}
 
 # Function to process text and extract zone provisions
 def extract_zone_setbacks(text, document_name=""):
 zones_found = []
 
 # Enhanced patterns for zone setback extraction
 patterns = [
 # Direct zone references with setbacks
 r'Zone ([A-Z]+\d+[A-Z]*)[^\w]*(?:.*?)(?:setback|minimum distance|metres?|meters?)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
 
 # Zone in sentence with setback measurements
 r'([A-Z]+\d+[A-Z]*)[^\w]*(?:.*?)(?:setback|distance|minimum)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
 
 # Front/side/rear setback patterns
 r'(?:front|side|rear)\s+setback[s]?[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)[^\w]*Zone ([A-Z]+\d+[A-Z]*)',
 r'Zone ([A-Z]+\d+[A-Z]*)[^\w]*(?:front|side|rear)\s+setback[s]?[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
 ]
 
 for pattern in patterns:
 matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
 for match in matches:
 if len(match) == 2:
 # Determine which is zone and which is measurement
 if re.match(r'^[A-Z]+\d+[A-Z]*$', match[0]):
 zone, measurement = match[0], match[1]
 else:
 zone, measurement = match[1], match[0]
 
 zones_found.append({
 'zone': zone,
 'measurement': float(measurement),
 'document': document_name,
 'context': text[:200]
 })
 
 return zones_found
 
 # Process different JSON file types
 json_sources = [
 # LangExtract verified outputs
 ('langextract_verified_output', '*.json'),
 
 # AutoSchemaKG outputs
 ('autoschemakg_output_ollama_final/kg_extraction', '*.json'),
 
 # Validated outputs
 ('validated_outputs', '*.json'),
 
 # Monitored pipeline outputs
 ('monitored_pipeline_output', '*.json'),
 
 # Output directory
 ('output', '**/*.json'),
 ]
 
 total_files_processed = 0
 
 for directory, pattern in json_sources:
 if os.path.exists(directory):
 print(f"\nProcessing {directory}...")
 
 for json_file in Path(directory).rglob(pattern):
 if json_file.is_file() and json_file.stat().st_size < 10_000_000: # Skip files > 10MB
 try:
 total_files_processed += 1
 
 with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
 content = f.read()
 
 # Try to parse as JSON
 try:
 data = json.loads(content)
 except json.JSONDecodeError:
 # Try parsing line by line (JSONL format)
 data = []
 for line in content.split('\n'):
 if line.strip():
 try:
 data.append(json.loads(line))
 except json.JSONDecodeError:
 continue
 
 # Process the JSON data
 if isinstance(data, list):
 for item in data:
 text_content = ""
 doc_name = json_file.name
 
 # Extract text from various JSON structures
 if isinstance(item, dict):
 if 'text' in item:
 text_content = str(item['text'])
 elif 'content' in item:
 text_content = str(item['content'])
 elif 'original_text' in item:
 text_content = str(item['original_text'])
 elif 'provision_text' in item:
 text_content = str(item['provision_text'])
 
 # Get document name if available
 if 'document_id' in item:
 doc_name = item['document_id']
 elif 'document_name' in item:
 doc_name = item['document_name']
 elif 'metadata' in item and 'document_name' in item['metadata']:
 doc_name = item['metadata']['document_name']
 
 if text_content and len(text_content) > 20:
 zone_matches = extract_zone_setbacks(text_content, doc_name)
 for match in zone_matches:
 key = f"{match['zone']}_{match['document']}"
 if key not in zone_provisions:
 zone_provisions[key] = []
 zone_provisions[key].append(match)
 
 elif isinstance(data, dict):
 # Single JSON object
 text_content = ""
 doc_name = json_file.name
 
 if 'text' in data:
 text_content = str(data['text'])
 elif 'content' in data:
 text_content = str(data['content'])
 elif 'original_text' in data:
 text_content = str(data['original_text'])
 
 if 'document_id' in data:
 doc_name = data['document_id']
 elif 'document_name' in data:
 doc_name = data['document_name']
 
 if text_content and len(text_content) > 20:
 zone_matches = extract_zone_setbacks(text_content, doc_name)
 for match in zone_matches:
 key = f"{match['zone']}_{match['document']}"
 if key not in zone_provisions:
 zone_provisions[key] = []
 zone_provisions[key].append(match)
 
 except Exception as e:
 print(f"Error processing {json_file}: {e}")
 continue
 
 print(f"\nProcessed {total_files_processed} JSON files")
 print(f"Found {len(zone_provisions)} unique zone-document combinations")
 
 # Display findings
 for key, provisions in zone_provisions.items():
 if provisions:
 zone = provisions[0]['zone']
 doc = provisions[0]['document']
 measurements = [p['measurement'] for p in provisions]
 print(f"\n{zone} in {doc[:50]}:")
 print(f" Setbacks: {sorted(set(measurements))} metres")
 print(f" Context: {provisions[0]['context'][:100]}...")
 
 # Update database with found zone relationships
 if zone_provisions:
 print(f"\nUpdating database with {len(zone_provisions)} zone relationships...")
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 updates_made = 0
 
 try:
 for key, provisions in zone_provisions.items():
 if not provisions:
 continue
 
 zone = provisions[0]['zone']
 document = provisions[0]['document']
 
 # Update provisions that match this document and mention this zone
 cursor.execute("""
 UPDATE regulatory_provisions 
 SET zone = ?
 WHERE (document_id LIKE ? OR provision_text LIKE ?)
 AND (zone IS NULL OR zone = '')
 """, (
 zone,
 f'%{document.replace(".json", "").replace("_", "%")}%',
 f'%{zone}%'
 ))
 
 rows_updated = cursor.rowcount
 if rows_updated > 0:
 print(f"Updated {rows_updated} records with zone {zone}")
 updates_made += rows_updated
 
 conn.commit()
 
 # Check final results
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL AND zone != ''")
 zone_count = cursor.fetchone()[0]
 
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
 total_count = cursor.fetchone()[0]
 
 print(f"\nFINAL RESULTS:")
 print(f"Records with zones: {zone_count}/{total_count} ({zone_count/total_count*100:.1f}%)")
 print(f"New updates: {updates_made}")
 
 return zone_count
 
 except Exception as e:
 print(f"Database error: {e}")
 conn.rollback()
 return 0
 finally:
 conn.close()
 
 return 0

if __name__ == "__main__":
 result = extract_zones_from_all_sources()