#!/usr/bin/env python3
"""
Extract All Zone-Specific Rules from 4,649+ JSON Files
====================================================
Comprehensive extraction of zone setback rules for PRP-K3 implementation
"""

import json
import sqlite3
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ZoneRuleExtractor:
 def __init__(self):
 self.zone_rules = []
 self.processed_files = 0
 self.extraction_patterns = self.build_patterns()
 
 def build_patterns(self) -> List[Dict]:
 """Build comprehensive extraction patterns for different JSON structures"""
 return [
 # Pattern 1: Direct compliance rules (like inner-west-compliance-rules.json)
 {
 'name': 'compliance_rules',
 'structure': 'rules[]',
 'zone_path': ['applies_to', 'zones'],
 'setback_path': ['requirements'],
 'confidence': 0.95
 },
 
 # Pattern 2: Regulatory provisions with zone mentions
 {
 'name': 'regulatory_provisions', 
 'structure': 'provisions[]',
 'zone_extraction': r'Zone (R[1-5]|B[1-8]|IN[1-4]|SP[1-5])',
 'setback_extraction': r'(?:setback|minimum distance)[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)',
 'confidence': 0.8
 },
 
 # Pattern 3: Development controls with zone_applicable
 {
 'name': 'development_controls',
 'structure': 'controls[]',
 'zone_path': ['zone_applicable'],
 'setback_path': ['control_type', 'value_numeric'],
 'confidence': 0.85
 },
 
 # Pattern 4: AutoSchemaKG extractions
 {
 'name': 'autoschema_kg',
 'structure': 'event_entity_relation_dict[]',
 'zone_extraction': r'Zone (R[1-5]|B[1-8]|IN[1-4]|SP[1-5])',
 'setback_extraction': r'(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m).*setback',
 'confidence': 0.75
 },
 
 # Pattern 5: Table data with zone references
 {
 'name': 'table_data',
 'structure': 'table_body',
 'zone_extraction': r'(R[1-5]|B[1-8]|IN[1-4]|SP[1-5]).*Residential|Commercial|Industrial',
 'setback_extraction': r'(\d+(?:\.\d+)?)\s*(?:m|metres?|meters?).*setback',
 'confidence': 0.7
 }
 ]
 
 def extract_from_compliance_rules(self, data: Dict, file_path: str) -> List[Dict]:
 """Extract from structured compliance rules (highest confidence)"""
 rules = []
 
 if 'rules' not in data:
 return rules
 
 for rule in data['rules']:
 try:
 # Extract basic rule information
 rule_id = rule.get('id', f"auto_{len(rules)}")
 jurisdiction = rule.get('jurisdiction', 'DCP')
 authority = rule.get('authority', 'Unknown')
 
 # Extract zone information
 applies_to = rule.get('applies_to', {})
 zones = applies_to.get('zones', [])
 council = applies_to.get('former_council', applies_to.get('lga', 'Unknown'))
 
 # Extract setback requirements
 requirements = rule.get('requirements', [])
 
 for req in requirements:
 if req.get('type') == 'min_setback':
 for zone in zones:
 zone_rule = {
 'rule_id': f"{rule_id}_{zone}_{req.get('subtype')}",
 'zone': zone,
 'council': council,
 'boundary_type': req.get('subtype', 'unknown'),
 'base_value': float(req.get('value', 0)),
 'unit': req.get('units', 'metres'),
 'operator': req.get('operator', '>='),
 'authority_type': jurisdiction,
 'precedence_level': self.get_precedence(jurisdiction),
 'conditions': req.get('context', ''),
 'source_document': rule.get('source', {}).get('document', file_path),
 'source_clause': rule.get('source', {}).get('clause', ''),
 'effective_date': rule.get('source', {}).get('effective_date', ''),
 'quality_score': rule.get('extraction_metadata', {}).get('quality_score', 0.95),
 'extraction_method': 'compliance_rules',
 'source_file': file_path,
 'confidence': 0.95
 }
 rules.append(zone_rule)
 
 except Exception as e:
 logger.warning(f"Error processing compliance rule in {file_path}: {e}")
 
 return rules
 
 def extract_from_text_patterns(self, data: Any, file_path: str) -> List[Dict]:
 """Extract using regex patterns from various text structures"""
 rules = []
 
 # Convert data to searchable text
 text_content = self.extract_text_content(data)
 if not text_content or len(text_content) < 50:
 return rules
 
 # Find zone and setback combinations
 zone_setback_matches = self.find_zone_setback_combinations(text_content)
 
 for match in zone_setback_matches:
 try:
 zone_rule = {
 'rule_id': f"extracted_{match['zone']}_{match['boundary']}_{hash(match['context']) % 10000}",
 'zone': match['zone'],
 'council': self.extract_council_from_path(file_path),
 'boundary_type': match['boundary'],
 'base_value': match['value'],
 'unit': match['unit'],
 'operator': '>=',
 'authority_type': self.infer_authority_from_path(file_path),
 'precedence_level': self.get_precedence_from_path(file_path),
 'conditions': match['context'][:200],
 'source_document': self.extract_document_name(file_path),
 'source_clause': '',
 'effective_date': '',
 'quality_score': match['confidence'],
 'extraction_method': 'text_patterns',
 'source_file': file_path,
 'confidence': match['confidence']
 }
 rules.append(zone_rule)
 
 except Exception as e:
 logger.warning(f"Error processing text pattern in {file_path}: {e}")
 
 return rules
 
 def find_zone_setback_combinations(self, text: str) -> List[Dict]:
 """Find zone-setback combinations using advanced patterns"""
 combinations = []
 
 # Pattern 1: Direct zone-setback statements
 pattern1 = r'Zone (R[1-5]|B[1-8]|IN[1-4]|SP[1-5])[^\d]*(?:.*?)(?:front|side|rear)?\s*setback[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)'
 matches1 = re.finditer(pattern1, text, re.IGNORECASE | re.DOTALL)
 
 for match in matches1:
 zone = match.group(1)
 value = float(match.group(2))
 boundary = self.infer_boundary_type(match.group(0))
 context_start = max(0, match.start() - 100)
 context_end = min(len(text), match.end() + 100)
 context = text[context_start:context_end].replace('\n', ' ').strip()
 
 combinations.append({
 'zone': zone,
 'value': value,
 'unit': 'metres',
 'boundary': boundary,
 'context': context,
 'confidence': 0.8
 })
 
 # Pattern 2: Setback tables with zone columns
 pattern2 = r'(R[1-5]|B[1-8]|IN[1-4]|SP[1-5])[^\d]*(\d+(?:\.\d+)?)\s*(?:metres?|meters?|m)'
 matches2 = re.finditer(pattern2, text, re.IGNORECASE)
 
 for match in matches2:
 if 'setback' in text[max(0, match.start()-50):match.end()+50].lower():
 zone = match.group(1)
 value = float(match.group(2))
 boundary = self.infer_boundary_type(text[max(0, match.start()-100):match.end()+100])
 context_start = max(0, match.start() - 100)
 context_end = min(len(text), match.end() + 100)
 context = text[context_start:context_end].replace('\n', ' ').strip()
 
 combinations.append({
 'zone': zone,
 'value': value,
 'unit': 'metres',
 'boundary': boundary,
 'context': context,
 'confidence': 0.7
 })
 
 # Remove duplicates
 unique_combinations = []
 seen = set()
 
 for combo in combinations:
 key = (combo['zone'], combo['value'], combo['boundary'])
 if key not in seen:
 seen.add(key)
 unique_combinations.append(combo)
 
 return unique_combinations
 
 def extract_text_content(self, data: Any) -> str:
 """Extract searchable text from various JSON structures"""
 text_parts = []
 
 if isinstance(data, dict):
 # Common text fields
 text_fields = ['text', 'content', 'provision_text', 'regulatory_text', 
 'table_body', 'description', 'context', 'original_text']
 
 for field in text_fields:
 if field in data and data[field]:
 text_parts.append(str(data[field]))
 
 # Recursively extract from nested structures
 for key, value in data.items():
 if key in ['rules', 'provisions', 'controls', 'entities', 'items']:
 if isinstance(value, list):
 for item in value:
 text_parts.append(self.extract_text_content(item))
 else:
 text_parts.append(self.extract_text_content(value))
 
 elif isinstance(data, list):
 for item in data:
 text_parts.append(self.extract_text_content(item))
 
 elif isinstance(data, str):
 text_parts.append(data)
 
 return ' '.join(text_parts)
 
 def infer_boundary_type(self, text: str) -> str:
 """Infer boundary type from context"""
 text_lower = text.lower()
 
 if 'front' in text_lower:
 return 'front'
 elif 'rear' in text_lower or 'back' in text_lower:
 return 'rear' 
 elif 'side' in text_lower:
 return 'side'
 else:
 return 'general'
 
 def extract_council_from_path(self, file_path: str) -> str:
 """Extract council name from file path"""
 path_lower = file_path.lower()
 
 councils = ['ashfield', 'leichhardt', 'marrickville', 'inner west']
 
 for council in councils:
 if council in path_lower:
 return council.title()
 
 return 'Inner West'
 
 def infer_authority_from_path(self, file_path: str) -> str:
 """Infer authority type from file path"""
 path_lower = file_path.lower()
 
 if 'sepp' in path_lower or 'state environmental planning policy' in path_lower:
 return 'SEPP'
 elif 'lep' in path_lower or 'local environmental plan' in path_lower:
 return 'LEP'
 elif 'dcp' in path_lower or 'development control plan' in path_lower:
 return 'DCP'
 else:
 return 'DCP' # Default assumption
 
 def get_precedence(self, authority: str) -> int:
 """Get legal precedence level"""
 precedence_map = {
 'SEPP': 1,
 'LEP': 2, 
 'DCP': 3
 }
 return precedence_map.get(authority, 3)
 
 def get_precedence_from_path(self, file_path: str) -> int:
 """Get precedence from file path"""
 authority = self.infer_authority_from_path(file_path)
 return self.get_precedence(authority)
 
 def extract_document_name(self, file_path: str) -> str:
 """Extract readable document name from file path"""
 filename = Path(file_path).stem
 
 # Clean up common filename patterns
 cleaned = filename.replace('_', ' ').replace('-', ' ')
 cleaned = re.sub(r'\s+', ' ', cleaned).strip()
 
 return cleaned
 
 def process_single_file(self, file_path: Path) -> List[Dict]:
 """Process a single JSON file and extract zone rules"""
 rules = []
 
 try:
 # Skip very large files (>50MB) for performance
 if file_path.stat().st_size > 50_000_000:
 logger.info(f"Skipping large file: {file_path}")
 return rules
 
 with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
 content = f.read()
 
 # Try to parse as JSON
 try:
 data = json.loads(content)
 except json.JSONDecodeError:
 # Try parsing as JSONL (multiple JSON objects)
 data = []
 for line in content.split('\n'):
 if line.strip():
 try:
 data.append(json.loads(line))
 except json.JSONDecodeError:
 continue
 
 # Extract using different strategies
 str_path = str(file_path)
 
 # Strategy 1: Structured compliance rules (highest confidence)
 if isinstance(data, dict) and 'rules' in data:
 rules.extend(self.extract_from_compliance_rules(data, str_path))
 
 # Strategy 2: Text pattern extraction
 if not rules: # Only if no high-confidence rules found
 rules.extend(self.extract_from_text_patterns(data, str_path))
 
 self.processed_files += 1
 
 if rules:
 logger.info(f"Extracted {len(rules)} rules from {file_path.name}")
 
 except Exception as e:
 logger.warning(f"Error processing {file_path}: {e}")
 
 return rules
 
 def process_all_files(self) -> List[Dict]:
 """Process all JSON files in the project"""
 logger.info("Starting comprehensive zone rule extraction from 4,649+ JSON files")
 
 # Get all JSON files
 json_files = list(Path('.').rglob('*.json'))
 total_files = len(json_files)
 
 logger.info(f"Found {total_files} JSON files to process")
 
 all_rules = []
 
 # Priority files to process first (high-confidence sources)
 priority_files = [
 'public/regulatory-data/inner-west-compliance-rules.json',
 'compliance_result.json',
 'multimodal_relationships_complete.json'
 ]
 
 # Process priority files first
 for priority_file in priority_files:
 if Path(priority_file).exists():
 logger.info(f"Processing priority file: {priority_file}")
 rules = self.process_single_file(Path(priority_file))
 all_rules.extend(rules)
 
 # Process remaining files
 processed_priority = set(priority_files)
 
 for i, json_file in enumerate(json_files):
 if str(json_file) in processed_priority:
 continue
 
 if i % 100 == 0:
 logger.info(f"Progress: {i}/{total_files} files processed, {len(all_rules)} rules extracted")
 
 rules = self.process_single_file(json_file)
 all_rules.extend(rules)
 
 logger.info(f"Extraction complete: {len(all_rules)} total rules from {self.processed_files} files")
 
 return all_rules
 
 def save_to_database(self, rules: List[Dict]) -> None:
 """Save extracted rules to database"""
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Create zone_setback_rules table
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS zone_setback_rules (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 rule_id TEXT UNIQUE,
 zone TEXT NOT NULL,
 council TEXT,
 boundary_type TEXT,
 base_value REAL,
 unit TEXT DEFAULT 'metres',
 operator TEXT DEFAULT '>=',
 authority_type TEXT,
 precedence_level INTEGER,
 conditions TEXT,
 source_document TEXT,
 source_clause TEXT,
 effective_date TEXT,
 quality_score REAL,
 extraction_method TEXT,
 source_file TEXT,
 confidence REAL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
 )
 ''')
 
 # Create indexes
 cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_lookup ON zone_setback_rules (zone, council, boundary_type)')
 cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_precedence ON zone_setback_rules (zone, precedence_level)')
 
 # Insert rules
 inserted = 0
 for rule in rules:
 try:
 cursor.execute('''
 INSERT OR REPLACE INTO zone_setback_rules (
 rule_id, zone, council, boundary_type, base_value, unit, operator,
 authority_type, precedence_level, conditions, source_document,
 source_clause, effective_date, quality_score, extraction_method,
 source_file, confidence
 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 ''', (
 rule['rule_id'], rule['zone'], rule['council'], rule['boundary_type'],
 rule['base_value'], rule['unit'], rule['operator'], rule['authority_type'],
 rule['precedence_level'], rule['conditions'], rule['source_document'],
 rule['source_clause'], rule['effective_date'], rule['quality_score'],
 rule['extraction_method'], rule['source_file'], rule['confidence']
 ))
 inserted += 1
 except Exception as e:
 logger.warning(f"Error inserting rule {rule.get('rule_id')}: {e}")
 
 conn.commit()
 conn.close()
 
 logger.info(f"Saved {inserted} zone rules to database")
 
 return inserted

def main():
 """Main execution function"""
 extractor = ZoneRuleExtractor()
 
 # Extract all zone rules
 all_rules = extractor.process_all_files()
 
 # Filter for quality and relevance
 quality_rules = [
 rule for rule in all_rules 
 if rule['confidence'] >= 0.7 and rule['base_value'] > 0
 ]
 
 logger.info(f"Filtered to {len(quality_rules)} high-quality rules")
 
 # Save to database
 saved_count = extractor.save_to_database(quality_rules)
 
 # Generate summary
 print("\n" + "="*60)
 print("ZONE RULE EXTRACTION SUMMARY")
 print("="*60)
 print(f"Files processed: {extractor.processed_files}")
 print(f"Total rules extracted: {len(all_rules)}")
 print(f"High-quality rules: {len(quality_rules)}")
 print(f"Rules saved to database: {saved_count}")
 
 # Show zone distribution
 zones = {}
 for rule in quality_rules:
 zone = rule['zone']
 if zone not in zones:
 zones[zone] = 0
 zones[zone] += 1
 
 print(f"\nZone distribution:")
 for zone, count in sorted(zones.items()):
 print(f" {zone}: {count} rules")
 
 print(f"\nDatabase table: zone_setback_rules")
 print(f"Ready for PRP-K3 implementation")

if __name__ == "__main__":
 main()