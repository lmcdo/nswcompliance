#!/usr/bin/env python3
"""
PRP-P2: Phase 2 - Land Use Table Parsing
Parses structured LEP land use tables to extract zone-specific development permissions
"""

import sqlite3
import re
import json
import time
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import csv

class LEPTableParser:
 """
 Parses LEP land use tables to extract zone/development type/permission combinations
 """
 
 def __init__(self, db_path: str = "nsw_planning.db"):
 self.conn = sqlite3.connect(db_path)
 self.cur = self.conn.cursor()
 
 # Development type standardization mappings
 self.development_type_mappings = {
 'dwelling house': 'dwelling_house',
 'dwelling houses': 'dwelling_house', 
 'dual occupancy': 'dual_occupancy',
 'dual occupancies': 'dual_occupancy',
 'multi dwelling housing': 'multi_dwelling_housing',
 'multi-dwelling housing': 'multi_dwelling_housing',
 'residential flat building': 'residential_flat_building',
 'residential flat buildings': 'residential_flat_building',
 'apartment building': 'residential_flat_building',
 'apartments': 'residential_flat_building',
 'townhouse': 'multi_dwelling_housing',
 'townhouses': 'multi_dwelling_housing',
 'villa': 'multi_dwelling_housing',
 'villas': 'multi_dwelling_housing',
 'shop': 'retail_premises',
 'shops': 'retail_premises',
 'retail premises': 'retail_premises',
 'office premises': 'office_premises',
 'offices': 'office_premises',
 'commercial premises': 'commercial_premises',
 'business premises': 'business_premises',
 'warehouse': 'warehouse_or_distribution_centre',
 'warehouses': 'warehouse_or_distribution_centre',
 'storage premises': 'warehouse_or_distribution_centre',
 'light industry': 'light_industry',
 'light industrial': 'light_industry',
 'general industry': 'general_industry',
 'general industrial': 'general_industry',
 'heavy industry': 'general_industry',
 'mixed use': 'mixed_use_development',
 'mixed use development': 'mixed_use_development',
 'seniors housing': 'seniors_housing',
 "seniors' housing": 'seniors_housing',
 'group home': 'group_home',
 'group homes': 'group_home',
 'boarding house': 'boarding_house',
 'boarding houses': 'boarding_house',
 'child care centre': 'child_care_centre',
 'childcare centre': 'child_care_centre',
 'educational establishment': 'educational_establishment',
 'school': 'educational_establishment',
 'hospital': 'hospital',
 'medical centre': 'medical_centre',
 'place of public worship': 'place_of_public_worship',
 'community facility': 'community_facility',
 'recreation facility': 'recreation_facility_outdoor'
 }
 
 # Roman numeral mappings for tabular formats
 self.roman_numerals = {
 'I': 'permitted',
 'II': 'consent', 
 'III': 'prohibited',
 '1': 'permitted',
 '2': 'consent',
 '3': 'prohibited'
 }
 
 def setup_tables(self):
 """Create development permissions schema"""
 
 print("Creating PRP-P2 development permissions schema...")
 
 # Create development_permissions table
 self.cur.execute('''
 CREATE TABLE IF NOT EXISTS development_permissions (
 id INTEGER PRIMARY KEY,
 zone TEXT NOT NULL,
 development_type TEXT NOT NULL,
 permission_status TEXT NOT NULL, -- permitted/consent/prohibited
 conditions TEXT, -- Additional requirements
 source_provision_id INTEGER,
 lep_name TEXT,
 extraction_method TEXT, -- table_parsing/pattern_matching
 confidence_score REAL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(zone, development_type, source_provision_id)
 )
 ''')
 
 # Create indexes for performance
 self.cur.execute('CREATE INDEX IF NOT EXISTS idx_dev_perm_zone ON development_permissions(zone)')
 self.cur.execute('CREATE INDEX IF NOT EXISTS idx_dev_perm_type ON development_permissions(development_type)')
 
 # Create table for tracking parsing results
 self.cur.execute('''
 CREATE TABLE IF NOT EXISTS table_parsing_results (
 id INTEGER PRIMARY KEY,
 provision_id INTEGER,
 zone TEXT,
 table_type TEXT, -- standard_instrument/tabular_format/objective_list
 permissions_extracted INTEGER,
 parsing_status TEXT, -- success/partial/failed
 error_message TEXT,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
 )
 ''')
 
 self.conn.commit()
 print(" [DONE] Development permissions schema created")
 
 def identify_lep_tables(self):
 """Identify LEP provisions containing land use tables"""
 
 print("\nIdentifying LEP provisions with land use tables...")
 
 query = '''
 SELECT id, zone, provision_text, document_id
 FROM regulatory_provisions 
 WHERE document_id IN (SELECT id FROM documents WHERE document_type = 'LEP')
 AND provision_text IS NOT NULL
 AND (
 provision_text LIKE '%Land Use Table%'
 OR provision_text LIKE '%Zoning Table%'
 OR provision_text LIKE '%Permitted%Prohibited%'
 OR provision_text LIKE '%I%II%III%'
 OR provision_text LIKE '%zone objectives%'
 OR provision_text LIKE '%following development%'
 OR provision_text LIKE '%purposes%permitted%'
 OR provision_text LIKE '%development may be carried out%'
 OR provision_text LIKE '%without consent%'
 OR provision_text LIKE '%with consent%'
 )
 ORDER BY zone
 '''
 
 self.cur.execute(query)
 lep_provisions = self.cur.fetchall()
 
 print(f" Found {len(lep_provisions)} LEP provisions with potential table structures")
 
 return lep_provisions
 
 def parse_standard_instrument_table(self, text: str, zone: str, provision_id: int) -> List[Dict]:
 """Parse standard instrument format land use table"""
 
 permissions = []
 
 # Look for numbered sections (2, 3, 4 for permitted without consent, with consent, prohibited)
 sections = {
 'permitted': [
 r'2\s+Permitted without consent.*?(?=3\s|4\s|$)',
 r'permitted without consent.*?(?=permitted with consent|prohibited|$)',
 r'following development.*?permitted.*?(?=\(|\d+\.|$)'
 ],
 'consent': [
 r'3\s+Permitted with consent.*?(?=4\s|$)',
 r'permitted with consent.*?(?=prohibited|$)',
 r'following development.*?consent.*?(?=\(|\d+\.|$)'
 ],
 'prohibited': [
 r'4\s+Prohibited.*?(?=$)',
 r'prohibited.*?(?=$)',
 r'following development.*?prohibited.*?(?=\(|\d+\.|$)'
 ]
 }
 
 for permission_status, patterns in sections.items():
 for pattern in patterns:
 matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
 
 for match in matches:
 section_text = match.group(0)
 
 # Extract development types from this section
 dev_types = self.extract_development_types_from_section(section_text)
 
 for dev_type in dev_types:
 standardized_type = self.standardize_development_type(dev_type)
 if standardized_type:
 permissions.append({
 'zone': zone,
 'development_type': standardized_type,
 'permission_status': permission_status,
 'conditions': None,
 'source_provision_id': provision_id,
 'extraction_method': 'standard_instrument_parsing',
 'confidence_score': 0.9
 })
 
 return permissions
 
 def parse_tabular_format(self, text: str, zone: str, provision_id: int) -> List[Dict]:
 """Parse matrix-style tabular format"""
 
 permissions = []
 
 # Look for tabular patterns with Roman numerals or numbers
 lines = text.split('\n')
 
 for line in lines:
 line = line.strip()
 if not line:
 continue
 
 # Look for patterns like "Development Type | Zone R2 | Zone R3"
 # or "Dwelling houses I II III"
 
 # Extract development type from start of line
 dev_type_match = None
 for dev_type in self.development_type_mappings.keys():
 if line.lower().startswith(dev_type.lower()):
 dev_type_match = dev_type
 break
 
 if dev_type_match:
 standardized_type = self.standardize_development_type(dev_type_match)
 if standardized_type:
 # Look for permission indicators in the line
 remaining_text = line[len(dev_type_match):].strip()
 
 # Check for Roman numerals or numbers
 for indicator, permission in self.roman_numerals.items():
 if indicator in remaining_text:
 permissions.append({
 'zone': zone,
 'development_type': standardized_type,
 'permission_status': permission,
 'conditions': None,
 'source_provision_id': provision_id,
 'extraction_method': 'tabular_parsing',
 'confidence_score': 0.8
 })
 break
 
 return permissions
 
 def parse_objective_list_format(self, text: str, zone: str, provision_id: int) -> List[Dict]:
 """Parse objective list format"""
 
 permissions = []
 
 # Look for list patterns with (a), (b), (c) or bullet points
 list_patterns = [
 r'\([a-z]\)\s*([^()]+?)(?=\([a-z]\)|$)',
 r'[•·]\s*([^•·\n]+)',
 r'[-*]\s*([^-*\n]+)'
 ]
 
 for pattern in list_patterns:
 matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
 
 for match in matches:
 item_text = match.group(1).strip()
 
 # Extract development types from list item
 dev_types = self.extract_development_types_from_section(item_text)
 
 # Determine permission status from context
 permission_status = 'permitted' # Default for objective lists
 if 'prohibited' in item_text.lower() or 'not permitted' in item_text.lower():
 permission_status = 'prohibited'
 elif 'consent' in item_text.lower():
 permission_status = 'consent'
 
 for dev_type in dev_types:
 standardized_type = self.standardize_development_type(dev_type)
 if standardized_type:
 permissions.append({
 'zone': zone,
 'development_type': standardized_type,
 'permission_status': permission_status,
 'conditions': None,
 'source_provision_id': provision_id,
 'extraction_method': 'objective_list_parsing',
 'confidence_score': 0.7
 })
 
 return permissions
 
 def extract_development_types_from_section(self, text: str) -> List[str]:
 """Extract development types from a section of text"""
 
 dev_types = []
 text_lower = text.lower()
 
 # Look for development types in the mappings
 for original_type in self.development_type_mappings.keys():
 if original_type.lower() in text_lower:
 dev_types.append(original_type)
 
 # Remove duplicates while preserving order
 seen = set()
 unique_types = []
 for dt in dev_types:
 if dt not in seen:
 seen.add(dt)
 unique_types.append(dt)
 
 return unique_types
 
 def standardize_development_type(self, dev_type: str) -> Optional[str]:
 """Standardize development type using mappings"""
 
 return self.development_type_mappings.get(dev_type.lower())
 
 def determine_table_type(self, text: str) -> str:
 """Determine the type of table structure"""
 
 text_lower = text.lower()
 
 # Check for standard instrument patterns
 if ('permitted without consent' in text_lower and 
 'permitted with consent' in text_lower and 
 'prohibited' in text_lower):
 return 'standard_instrument'
 
 # Check for tabular format with Roman numerals
 if re.search(r'\b(I|II|III)\b', text) and ('zone' in text_lower or 'development' in text_lower):
 return 'tabular_format'
 
 # Check for objective list format
 if re.search(r'\([a-z]\)', text) or '•' in text or text.count('-') > 3:
 return 'objective_list'
 
 return 'unknown'
 
 def execute_table_parsing(self):
 """Execute table parsing on identified LEP provisions"""
 
 print("\nExecuting LEP table parsing...")
 
 lep_provisions = self.identify_lep_tables()
 
 all_permissions = []
 parsing_results = []
 processed = 0
 
 for prov_id, zone, text, doc_id in lep_provisions:
 if not text or not zone:
 continue
 
 try:
 # Determine table type
 table_type = self.determine_table_type(text)
 
 # Parse based on table type
 permissions = []
 if table_type == 'standard_instrument':
 permissions = self.parse_standard_instrument_table(text, zone, prov_id)
 elif table_type == 'tabular_format':
 permissions = self.parse_tabular_format(text, zone, prov_id)
 elif table_type == 'objective_list':
 permissions = self.parse_objective_list_format(text, zone, prov_id)
 
 # Add LEP name from document
 self.cur.execute('SELECT pdf_name FROM documents WHERE id = ?', (doc_id,))
 doc_result = self.cur.fetchone()
 lep_name = doc_result[0] if doc_result else 'Unknown LEP'
 
 for perm in permissions:
 perm['lep_name'] = lep_name
 
 all_permissions.extend(permissions)
 
 # Track parsing results
 parsing_results.append({
 'provision_id': prov_id,
 'zone': zone,
 'table_type': table_type,
 'permissions_extracted': len(permissions),
 'parsing_status': 'success' if permissions else 'no_permissions',
 'error_message': None
 })
 
 except Exception as e:
 parsing_results.append({
 'provision_id': prov_id,
 'zone': zone,
 'table_type': 'unknown',
 'permissions_extracted': 0,
 'parsing_status': 'failed',
 'error_message': str(e)
 })
 
 processed += 1
 if processed % 20 == 0:
 print(f" Processed {processed}/{len(lep_provisions)} provisions...")
 
 # Insert permissions into database
 if all_permissions:
 insert_query = '''
 INSERT OR IGNORE INTO development_permissions 
 (zone, development_type, permission_status, conditions, source_provision_id, 
 lep_name, extraction_method, confidence_score)
 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
 '''
 
 values = [(p['zone'], p['development_type'], p['permission_status'], 
 p['conditions'], p['source_provision_id'], p['lep_name'],
 p['extraction_method'], p['confidence_score']) for p in all_permissions]
 
 self.cur.executemany(insert_query, values)
 
 # Insert parsing results
 if parsing_results:
 result_query = '''
 INSERT INTO table_parsing_results 
 (provision_id, zone, table_type, permissions_extracted, parsing_status, error_message)
 VALUES (?, ?, ?, ?, ?, ?)
 '''
 
 result_values = [(r['provision_id'], r['zone'], r['table_type'],
 r['permissions_extracted'], r['parsing_status'], 
 r['error_message']) for r in parsing_results]
 
 self.cur.executemany(result_query, result_values)
 
 self.conn.commit()
 
 print(f" [DONE] Parsed {len(all_permissions)} development permissions from {len(lep_provisions)} provisions")
 return len(all_permissions)
 
 def validate_parsing_results(self):
 """Validate table parsing results"""
 
 print("\nValidating table parsing results...")
 
 # Get statistics
 stats = self.get_parsing_statistics()
 
 # Generate validation sample
 validation_sample = self.generate_validation_sample()
 
 # Run automated validation
 validation_results = self.run_validation_tests()
 
 print(f" [DONE] Validation complete")
 print(f" Total permissions: {stats['total_permissions']}")
 print(f" Unique zones: {stats['unique_zones']}")
 print(f" Unique dev types: {stats['unique_dev_types']}")
 print(f" Average confidence: {stats['avg_confidence']:.2f}")
 
 return stats, validation_sample, validation_results
 
 def get_parsing_statistics(self) -> Dict:
 """Get parsing statistics"""
 
 # Total permissions
 self.cur.execute('SELECT COUNT(*) FROM development_permissions')
 total = self.cur.fetchone()[0]
 
 # Unique zones
 self.cur.execute('SELECT COUNT(DISTINCT zone) FROM development_permissions')
 zones = self.cur.fetchone()[0]
 
 # Unique development types
 self.cur.execute('SELECT COUNT(DISTINCT development_type) FROM development_permissions')
 dev_types = self.cur.fetchone()[0]
 
 # Permission status distribution
 self.cur.execute('''
 SELECT permission_status, COUNT(*) 
 FROM development_permissions 
 GROUP BY permission_status
 ''')
 permission_dist = dict(self.cur.fetchall())
 
 # Average confidence
 self.cur.execute('SELECT AVG(confidence_score) FROM development_permissions')
 avg_confidence = self.cur.fetchone()[0] or 0
 
 # Extraction methods
 self.cur.execute('''
 SELECT extraction_method, COUNT(*) 
 FROM development_permissions 
 GROUP BY extraction_method
 ''')
 methods = dict(self.cur.fetchall())
 
 return {
 'total_permissions': total,
 'unique_zones': zones,
 'unique_dev_types': dev_types,
 'permission_distribution': permission_dist,
 'avg_confidence': avg_confidence,
 'extraction_methods': methods
 }
 
 def generate_validation_sample(self, sample_size: int = 25) -> List[Dict]:
 """Generate sample for manual validation"""
 
 # Get stratified sample across zones and development types
 self.cur.execute('''
 SELECT id, zone, development_type, permission_status, 
 extraction_method, confidence_score, lep_name
 FROM development_permissions
 ORDER BY RANDOM()
 LIMIT ?
 ''', (sample_size,))
 
 sample = []
 for row in self.cur.fetchall():
 sample.append({
 'id': row[0],
 'zone': row[1],
 'development_type': row[2],
 'permission_status': row[3],
 'extraction_method': row[4],
 'confidence_score': row[5],
 'lep_name': row[6]
 })
 
 return sample
 
 def run_validation_tests(self) -> Dict:
 """Run automated validation tests"""
 
 results = {'tests': []}
 
 # Test 1: Minimum permissions extracted
 self.cur.execute('SELECT COUNT(*) FROM development_permissions')
 count = self.cur.fetchone()[0]
 results['tests'].append({
 'name': 'minimum_permissions',
 'expected': 200,
 'actual': count,
 'status': 'pass' if count >= 200 else 'fail'
 })
 
 # Test 2: Zone coverage
 self.cur.execute('SELECT COUNT(DISTINCT zone) FROM development_permissions')
 zones = self.cur.fetchone()[0]
 results['tests'].append({
 'name': 'zone_coverage',
 'expected': 10,
 'actual': zones,
 'status': 'pass' if zones >= 10 else 'fail'
 })
 
 # Test 3: Development type coverage
 self.cur.execute('SELECT COUNT(DISTINCT development_type) FROM development_permissions')
 dev_types = self.cur.fetchone()[0]
 results['tests'].append({
 'name': 'dev_type_coverage',
 'expected': 12,
 'actual': dev_types,
 'status': 'pass' if dev_types >= 12 else 'fail'
 })
 
 # Test 4: Permission status variety
 self.cur.execute('SELECT COUNT(DISTINCT permission_status) FROM development_permissions')
 statuses = self.cur.fetchone()[0]
 results['tests'].append({
 'name': 'permission_status_variety',
 'expected': 3,
 'actual': statuses,
 'status': 'pass' if statuses >= 3 else 'fail'
 })
 
 # Test 5: Average confidence
 self.cur.execute('SELECT AVG(confidence_score) FROM development_permissions')
 avg_confidence = self.cur.fetchone()[0] or 0
 results['tests'].append({
 'name': 'average_confidence',
 'expected': 0.75,
 'actual': avg_confidence,
 'status': 'pass' if avg_confidence >= 0.75 else 'fail'
 })
 
 # Calculate overall pass rate
 passed_tests = sum(1 for test in results['tests'] if test['status'] == 'pass')
 results['overall_pass_rate'] = passed_tests / len(results['tests'])
 results['overall_status'] = 'pass' if results['overall_pass_rate'] >= 0.8 else 'fail'
 
 return results
 
 def generate_deliverables(self, stats: Dict, validation_sample: List[Dict], validation_results: Dict):
 """Generate PRP-P2 deliverables"""
 
 print("\nGenerating deliverables...")
 
 # 1. table_parsing_report.json
 report = {
 'execution_timestamp': datetime.now().isoformat(),
 'parsing_statistics': stats,
 'validation_results': validation_results,
 'success_criteria': {
 'minimum_permissions': stats['total_permissions'] >= 200,
 'zone_coverage': stats['unique_zones'] >= 10,
 'dev_type_coverage': stats['unique_dev_types'] >= 12,
 'permission_variety': len(stats['permission_distribution']) >= 3,
 'average_confidence': stats['avg_confidence'] >= 0.75
 },
 'overall_success': validation_results['overall_status'] == 'pass'
 }
 
 with open('table_parsing_report.json', 'w') as f:
 json.dump(report, f, indent=2)
 
 # 2. parsing_validation_sample.csv
 with open('parsing_validation_sample.csv', 'w', newline='', encoding='utf-8') as f:
 if validation_sample:
 writer = csv.DictWriter(f, fieldnames=validation_sample[0].keys())
 writer.writeheader()
 writer.writerows(validation_sample)
 
 # 3. anomaly_report.json - Check for inconsistencies
 anomalies = self.identify_anomalies()
 with open('anomaly_report.json', 'w') as f:
 json.dump(anomalies, f, indent=2)
 
 print(" [DONE] Deliverables generated:")
 print(" - table_parsing_report.json")
 print(" - parsing_validation_sample.csv")
 print(" - anomaly_report.json")
 print(" - phase2_table_parser.py")
 
 def identify_anomalies(self) -> Dict:
 """Identify parsing anomalies and inconsistencies"""
 
 anomalies = {'inconsistencies': [], 'unusual_patterns': []}
 
 # Check for conflicting permissions for same zone/dev type
 self.cur.execute('''
 SELECT zone, development_type, GROUP_CONCAT(permission_status) as statuses, COUNT(*) as count
 FROM development_permissions
 GROUP BY zone, development_type
 HAVING COUNT(DISTINCT permission_status) > 1
 ''')
 
 conflicts = self.cur.fetchall()
 for zone, dev_type, statuses, count in conflicts:
 anomalies['inconsistencies'].append({
 'type': 'conflicting_permissions',
 'zone': zone,
 'development_type': dev_type,
 'statuses': statuses,
 'count': count
 })
 
 return anomalies
 
 def execute_prp_p2(self):
 """Execute complete PRP-P2 process"""
 
 print("="*60)
 print("PRP-P2: LEP LAND USE TABLE PARSING")
 print("="*60)
 
 start_time = time.time()
 
 # Step 1: Setup schema
 self.setup_tables()
 
 # Step 2: Execute parsing
 permissions_count = self.execute_table_parsing()
 
 # Step 3: Validate
 stats, validation_sample, validation_results = self.validate_parsing_results()
 
 # Step 4: Generate deliverables
 self.generate_deliverables(stats, validation_sample, validation_results)
 
 execution_time = time.time() - start_time
 
 print(f"\n{'='*60}")
 print("PRP-P2 EXECUTION COMPLETE")
 print(f"{'='*60}")
 print(f"Execution time: {execution_time:.1f} seconds")
 print(f"Overall status: {'SUCCESS' if validation_results['overall_status'] == 'pass' else 'NEEDS REVIEW'}")
 
 # Show completion checklist
 print(f"\nCOMPLETION CHECKLIST:")
 success_criteria = {
 'Minimum permissions (200+)': stats['total_permissions'] >= 200,
 'Zone coverage (10+)': stats['unique_zones'] >= 10,
 'Dev type coverage (12+)': stats['unique_dev_types'] >= 12,
 'Permission variety (3+ types)': len(stats['permission_distribution']) >= 3,
 'Average confidence (0.75+)': stats['avg_confidence'] >= 0.75
 }
 
 for criterion, passed in success_criteria.items():
 status = "[PASS]" if passed else "[FAIL]"
 print(f" {status} {criterion}")
 
 if all(success_criteria.values()):
 print(f"\n[SUCCESS] PRP-P2 SUCCESSFULLY COMPLETED - Ready for PRP-P3")
 else:
 print(f"\n[WARNING] PRP-P2 NEEDS REVIEW - Check failed criteria")
 
 return validation_results['overall_status'] == 'pass'


def main():
 """Main execution"""
 parser = LEPTableParser()
 success = parser.execute_prp_p2()
 return success


if __name__ == "__main__":
 main()