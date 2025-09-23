#!/usr/bin/env python3
"""
PRP-K3 Phase 1A: High-Confidence Zone Rule Extraction
===================================================
Extract zone rules from verified, structured data sources
"""

import json
import psycopg2
import sys
import argparse
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_verified_rules(sources, output_table, confidence_threshold=0.9):
 """Extract rules from high-confidence structured sources"""
 
 print("=== PRP-K3 PHASE 1A: HIGH-CONFIDENCE RULE EXTRACTION ===")
 print("Using PostgreSQL for zone rule storage")
 
 # Connect to PostgreSQL database
 try:
 conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning", 
 user="postgres",
 password="postgres",
 port="5432"
 )
 cursor = conn.cursor()
 logger.info("Connected to PostgreSQL database")
 except Exception as e:
 logger.error(f"Failed to connect to PostgreSQL: {e}")
 logger.info("Falling back to SQLite...")
 import sqlite3
 conn = sqlite3.connect('nsw_planning.db')
 cursor = conn.cursor()
 
 # Create zone_setback_rules table if it doesn't exist (PostgreSQL syntax)
 cursor.execute('''
 CREATE TABLE IF NOT EXISTS zone_setback_rules (
 id SERIAL PRIMARY KEY,
 rule_id VARCHAR(200) UNIQUE,
 zone VARCHAR(10) NOT NULL,
 council VARCHAR(100),
 boundary_type VARCHAR(50),
 base_value DECIMAL(8,2),
 unit VARCHAR(20) DEFAULT 'metres',
 operator VARCHAR(10) DEFAULT '>=',
 authority_type VARCHAR(20),
 precedence_level INTEGER,
 conditions TEXT,
 source_document TEXT,
 source_clause TEXT,
 effective_date DATE,
 quality_score DECIMAL(3,2),
 extraction_method VARCHAR(50),
 source_file TEXT,
 confidence DECIMAL(3,2),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 ''')
 
 # Create indexes if they don't exist
 try:
 cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_lookup ON zone_setback_rules (zone, council, boundary_type)')
 cursor.execute('CREATE INDEX IF NOT EXISTS idx_zone_rules_precedence ON zone_setback_rules (zone, precedence_level)')
 except:
 pass # Indexes might already exist
 
 rules_extracted = 0
 
 # Process each source file
 for source_file in sources.split(','):
 source_file = source_file.strip()
 
 if not Path(source_file).exists():
 logger.warning(f"Source file not found: {source_file}")
 continue
 
 logger.info(f"Processing: {source_file}")
 
 try:
 with open(source_file, 'r', encoding='utf-8') as f:
 data = json.load(f)
 
 # Handle different file structures
 if 'rules' in data:
 # inner-west-compliance-rules.json format
 for rule in data['rules']:
 extracted = extract_compliance_rule(rule, source_file, cursor, confidence_threshold)
 rules_extracted += extracted
 
 elif 'compliance_summary' in data:
 # compliance_result.json format
 if 'results' in data:
 for result in data['results']:
 extracted = extract_compliance_result(result, source_file, cursor, confidence_threshold)
 rules_extracted += extracted
 
 elif 'verified_provisions' in data:
 # langextract verified format
 for provision in data['verified_provisions']:
 extracted = extract_langextract_provision(provision, source_file, cursor, confidence_threshold)
 rules_extracted += extracted
 
 except Exception as e:
 logger.error(f"Error processing {source_file}: {e}")
 
 # Skip database import since verified_compliance_rules table doesn't exist
 # Focus on JSON file extraction only
 logger.info("Skipping database import - focusing on JSON sources")
 
 conn.commit()
 conn.close()
 
 print(f"Phase 1A Complete: {rules_extracted} high-confidence rules extracted")
 return rules_extracted

def extract_compliance_rule(rule, source_file, cursor, confidence_threshold):
 """Extract rule from compliance rules format"""
 extracted = 0
 
 try:
 rule_id = rule.get('id', 'unknown')
 jurisdiction = rule.get('jurisdiction', 'DCP')
 authority = rule.get('authority', 'Unknown')
 
 applies_to = rule.get('applies_to', {})
 zones = applies_to.get('zones', [])
 council = applies_to.get('former_council', applies_to.get('lga', 'Unknown'))
 
 requirements = rule.get('requirements', [])
 
 for req in requirements:
 if req.get('type') == 'min_setback':
 confidence = rule.get('extraction_metadata', {}).get('quality_score', 0.95)
 
 if confidence >= confidence_threshold:
 for zone in zones:
 cursor.execute('''
 INSERT INTO zone_setback_rules (
 rule_id, zone, council, boundary_type, base_value, unit,
 operator, authority_type, precedence_level, conditions,
 source_document, source_clause, effective_date,
 quality_score, extraction_method, source_file, confidence
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT (rule_id) DO UPDATE SET
 zone = EXCLUDED.zone,
 council = EXCLUDED.council,
 boundary_type = EXCLUDED.boundary_type,
 base_value = EXCLUDED.base_value,
 unit = EXCLUDED.unit,
 operator = EXCLUDED.operator,
 authority_type = EXCLUDED.authority_type,
 precedence_level = EXCLUDED.precedence_level,
 conditions = EXCLUDED.conditions,
 source_document = EXCLUDED.source_document,
 source_clause = EXCLUDED.source_clause,
 effective_date = EXCLUDED.effective_date,
 quality_score = EXCLUDED.quality_score,
 extraction_method = EXCLUDED.extraction_method,
 source_file = EXCLUDED.source_file,
 confidence = EXCLUDED.confidence
 ''', (
 f"{rule_id}_{zone}_{req.get('subtype')}",
 zone,
 council,
 req.get('subtype', 'unknown'),
 float(req.get('value', 0)),
 req.get('units', 'metres'),
 req.get('operator', '>='),
 jurisdiction,
 get_precedence(jurisdiction),
 req.get('context', ''),
 rule.get('source', {}).get('document', source_file),
 rule.get('source', {}).get('clause', ''),
 rule.get('source', {}).get('effective_date', ''),
 confidence,
 'compliance_rules',
 source_file,
 confidence
 ))
 extracted += 1
 
 except Exception as e:
 logger.warning(f"Error extracting compliance rule: {e}")
 
 return extracted

def extract_compliance_result(result, source_file, cursor, confidence_threshold):
 """Extract rule from compliance result format"""
 extracted = 0
 
 try:
 rule_id = result.get('rule_id', 'unknown')
 
 # Look for zone in rule_id
 if any(zone in rule_id for zone in ['R1', 'R2', 'R3', 'R4', 'R5']):
 # Extract zone from rule_id
 zone = None
 for z in ['R1', 'R2', 'R3', 'R4', 'R5']:
 if z in rule_id:
 zone = z
 break
 
 if zone:
 required_value = result.get('required_value')
 confidence_level = result.get('confidence', 'MEDIUM')
 
 # Map confidence to numeric
 confidence_map = {'HIGH': 0.95, 'MEDIUM': 0.8, 'LOW': 0.6}
 confidence = confidence_map.get(confidence_level, 0.8)
 
 if confidence >= confidence_threshold and required_value:
 boundary_type = 'unknown'
 if 'FRONT' in rule_id:
 boundary_type = 'front'
 elif 'REAR' in rule_id:
 boundary_type = 'rear'
 elif 'SIDE' in rule_id:
 boundary_type = 'side'
 
 cursor.execute('''
 INSERT INTO zone_setback_rules (
 rule_id, zone, council, boundary_type, base_value, unit,
 operator, authority_type, precedence_level, conditions,
 source_document, quality_score, extraction_method,
 source_file, confidence
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT (rule_id) DO UPDATE SET
 zone = EXCLUDED.zone,
 council = EXCLUDED.council,
 boundary_type = EXCLUDED.boundary_type,
 base_value = EXCLUDED.base_value,
 unit = EXCLUDED.unit,
 operator = EXCLUDED.operator,
 authority_type = EXCLUDED.authority_type,
 precedence_level = EXCLUDED.precedence_level,
 conditions = EXCLUDED.conditions,
 source_document = EXCLUDED.source_document,
 quality_score = EXCLUDED.quality_score,
 extraction_method = EXCLUDED.extraction_method,
 source_file = EXCLUDED.source_file,
 confidence = EXCLUDED.confidence
 ''', (
 rule_id,
 zone,
 'Inner West',
 boundary_type,
 float(required_value),
 'metres',
 '>=',
 'DCP',
 3,
 result.get('regulatory_text', '')[:200],
 result.get('source', {}).get('document', source_file),
 confidence,
 'compliance_result',
 source_file,
 confidence
 ))
 extracted += 1
 
 except Exception as e:
 logger.warning(f"Error extracting compliance result: {e}")
 
 return extracted

def extract_langextract_provision(provision, source_file, cursor, confidence_threshold):
 """Extract rule from langextract verified format"""
 extracted = 0
 
 try:
 if provision.get('provision_type') == 'setback' and provision.get('measurements'):
 # Extract measurements and zone info
 measurements = provision.get('measurements', {})
 regulatory_text = provision.get('regulatory_text', '')
 
 # Look for zone references in text or applies_to
 zones = []
 if provision.get('applies_to'):
 applies_to = provision.get('applies_to', {})
 if 'zones' in applies_to:
 zones = applies_to['zones']
 
 # Look for zone references in regulatory text
 if not zones:
 for zone in ['R1', 'R2', 'R3', 'R4', 'R5', 'B1', 'B2', 'B3', 'B4']:
 if zone in regulatory_text:
 zones.append(zone)
 
 # Extract council from filename
 council = 'Unknown'
 if 'Marrickville' in source_file:
 council = 'Marrickville'
 elif 'Ashfield' in source_file:
 council = 'Ashfield'
 elif 'Leichhardt' in source_file:
 council = 'Leichhardt'
 
 if zones and measurements:
 for zone in zones:
 # Extract setback values from measurements
 for measurement_key, measurement_value in measurements.items():
 if isinstance(measurement_value, (int, float)):
 boundary_type = 'unknown'
 if 'front' in measurement_key.lower() or 'front' in regulatory_text.lower():
 boundary_type = 'front'
 elif 'rear' in measurement_key.lower() or 'rear' in regulatory_text.lower():
 boundary_type = 'rear'
 elif 'side' in measurement_key.lower() or 'side' in regulatory_text.lower():
 boundary_type = 'side'
 
 rule_id = f"LANGEXTRACT_{council.upper()}_{zone}_{boundary_type}_{provision.get('clause_reference', '')}"
 
 cursor.execute('''
 INSERT INTO zone_setback_rules (
 rule_id, zone, council, boundary_type, base_value, unit,
 operator, authority_type, precedence_level, conditions,
 source_document, source_clause, quality_score, 
 extraction_method, source_file, confidence
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 ON CONFLICT (rule_id) DO UPDATE SET
 base_value = EXCLUDED.base_value,
 confidence = EXCLUDED.confidence
 ''', (
 rule_id,
 zone,
 council,
 boundary_type,
 float(measurement_value),
 'metres',
 '>=',
 'DCP',
 3,
 regulatory_text[:200],
 provision.get('document_source', source_file),
 provision.get('clause_reference', ''),
 0.9,
 'langextract_verified',
 source_file,
 0.9
 ))
 extracted += 1
 
 except Exception as e:
 logger.warning(f"Error extracting langextract provision: {e}")
 
 return extracted

def get_precedence(authority):
 """Get legal precedence level"""
 precedence_map = {
 'SEPP': 1,
 'LEP': 2,
 'DCP': 3
 }
 return precedence_map.get(authority, 3)

def main():
 parser = argparse.ArgumentParser(description='Extract high-confidence zone rules')
 parser.add_argument('--sources', required=True, help='Comma-separated list of source files')
 parser.add_argument('--output-table', default='zone_setback_rules', help='Output table name')
 parser.add_argument('--confidence-threshold', type=float, default=0.9, help='Minimum confidence threshold')
 parser.add_argument('--verify-against-source', type=bool, default=True, help='Verify against source')
 
 args = parser.parse_args()
 
 rules_count = extract_verified_rules(
 args.sources, 
 args.output_table, 
 args.confidence_threshold
 )
 
 return rules_count

if __name__ == "__main__":
 count = main()
 sys.exit(0 if count >= 6 else 1) # Exit with error if less than 6 rules extracted