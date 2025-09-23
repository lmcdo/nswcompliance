#!/usr/bin/env python3
"""
PRP-M2: SEPP/LEP Data Restructuring Engine
Extracts SEPP/LEP provisions into dedicated tables for pathway intelligence
"""

import psycopg2
import json
from datetime import datetime
from db_config import get_connection

class PRP_M2_Restructuring:
 def __init__(self):
 self.conn = get_connection()
 self.restructuring_report = {
 'start_time': datetime.now().isoformat(),
 'extraction_results': {},
 'table_creation': {},
 'total_sepp_extracted': 0,
 'total_lep_extracted': 0,
 'status': 'IN_PROGRESS'
 }

 def create_sepp_provisions_table(self):
 """Create optimized SEPP provisions table"""
 cursor = self.conn.cursor()

 sepp_schema = '''
 CREATE TABLE IF NOT EXISTS sepp_provisions (
 id SERIAL PRIMARY KEY,
 original_provision_id INTEGER REFERENCES regulatory_provisions(id),
 sepp_type TEXT NOT NULL, -- 'Exempt and Complying', 'Housing', etc.
 sepp_number TEXT, -- SEPP number/identifier
 provision_category TEXT, -- 'exempt', 'complying', 'prohibited'
 development_type TEXT,
 zone_applicability TEXT,
 provision_text TEXT NOT NULL,
 ref_number TEXT,
 page_number INTEGER,
 section_header TEXT,
 classification_confidence REAL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 extraction_method TEXT DEFAULT 'prp_m2_auto'
 )
 '''

 cursor.execute('DROP TABLE IF EXISTS sepp_provisions CASCADE')
 cursor.execute(sepp_schema)
 self.conn.commit()

 self.restructuring_report['table_creation']['sepp_provisions'] = {
 'status': 'created',
 'timestamp': datetime.now().isoformat()
 }

 print("SUCCESS SEPP provisions table created")

 def create_lep_provisions_table(self):
 """Create optimized LEP provisions table"""
 cursor = self.conn.cursor()

 lep_schema = '''
 CREATE TABLE IF NOT EXISTS lep_provisions (
 id SERIAL PRIMARY KEY,
 original_provision_id INTEGER REFERENCES regulatory_provisions(id),
 lep_name TEXT NOT NULL, -- 'Inner West LEP 2022', etc.
 lep_zone TEXT, -- R1, R2, B1, etc.
 provision_category TEXT, -- 'permitted', 'prohibited', 'consent'
 development_type TEXT,
 provision_text TEXT NOT NULL,
 ref_number TEXT,
 page_number INTEGER,
 section_header TEXT,
 classification_confidence REAL,
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 extraction_method TEXT DEFAULT 'prp_m2_auto'
 )
 '''

 cursor.execute('DROP TABLE IF EXISTS lep_provisions CASCADE')
 cursor.execute(lep_schema)
 self.conn.commit()

 self.restructuring_report['table_creation']['lep_provisions'] = {
 'status': 'created',
 'timestamp': datetime.now().isoformat()
 }

 print("SUCCESS LEP provisions table created")

 def extract_sepp_provisions(self):
 """Extract SEPP provisions using document type identification"""
 cursor = self.conn.cursor()

 # Strategy: Direct extraction from SEPP documents
 cursor.execute('''
 SELECT rp.*, d.pdf_name
 FROM regulatory_provisions rp
 JOIN documents d ON rp.document_id = d.id
 WHERE d.document_type = 'SEPP'
 ''')

 all_candidates = {}
 sepp_rows = cursor.fetchall()

 for row in sepp_rows:
 all_candidates[row[0]] = row # Use ID as key to deduplicate

 print(f"Found {len(all_candidates)} SEPP provisions from SEPP documents")

 # Insert into sepp_provisions table
 insert_sql = '''
 INSERT INTO sepp_provisions (
 original_provision_id, sepp_type, provision_category,
 development_type, zone_applicability, provision_text,
 ref_number, page_number, section_header, classification_confidence
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 '''

 sepp_insertions = 0

 for provision_id, row in all_candidates.items():
 # Extract SEPP type and category from document name and text
 provision_text = row[4] or '' # provision_text column
 ref_number = row[3] or '' # ref_number column
 document_name = row[-1] or '' # pdf_name from JOIN

 # Determine SEPP type from document name (more reliable)
 sepp_type = 'General SEPP'
 if 'Exempt and Complying' in document_name:
 sepp_type = 'Exempt and Complying'
 elif 'Housing' in document_name:
 sepp_type = 'Housing'
 elif 'Infrastructure' in document_name:
 sepp_type = 'Infrastructure'
 elif 'Planning Systems' in document_name:
 sepp_type = 'Planning Systems'

 # Determine provision category from text content
 category = 'general'
 text_lower = provision_text.lower()
 if 'exempt development' in text_lower or 'exempted development' in text_lower:
 category = 'exempt'
 elif 'complying development' in text_lower:
 category = 'complying'
 elif 'prohibited' in text_lower or 'not permitted' in text_lower:
 category = 'prohibited'
 elif 'permitted without consent' in text_lower:
 category = 'permitted'
 elif 'permitted with consent' in text_lower or 'consent required' in text_lower:
 category = 'consent'

 cursor.execute(insert_sql, (
 row[0], # original_provision_id
 sepp_type, # sepp_type
 category, # provision_category
 row[6] or '', # development_type
 row[5] or '', # zone_applicability (zone column)
 row[4], # provision_text
 row[3], # ref_number
 row[7], # page_number
 row[8], # section_header
 row[13] or 0.8 # classification_confidence
 ))

 sepp_insertions += 1

 self.conn.commit()

 self.restructuring_report['extraction_results']['sepp_provisions'] = {
 'candidates_found': len(all_candidates),
 'records_extracted': sepp_insertions,
 'extraction_success': sepp_insertions > 0
 }

 self.restructuring_report['total_sepp_extracted'] = sepp_insertions

 print(f"SUCCESS Extracted {sepp_insertions:,} SEPP provisions")

 def extract_lep_provisions(self):
 """Extract LEP provisions using document type identification"""
 cursor = self.conn.cursor()

 # Strategy: Direct extraction from LEP documents
 cursor.execute('''
 SELECT rp.*, d.pdf_name
 FROM regulatory_provisions rp
 JOIN documents d ON rp.document_id = d.id
 WHERE d.document_type = 'LEP'
 ''')

 all_candidates = {}
 lep_rows = cursor.fetchall()

 for row in lep_rows:
 all_candidates[row[0]] = row # Use ID as key to deduplicate

 print(f"Found {len(all_candidates)} LEP provisions from LEP documents")

 # Insert into lep_provisions table
 insert_sql = '''
 INSERT INTO lep_provisions (
 original_provision_id, lep_name, lep_zone, provision_category,
 development_type, provision_text, ref_number, page_number,
 section_header, classification_confidence
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 '''

 lep_insertions = 0

 for provision_id, row in all_candidates.items():
 provision_text = row[4] or ''
 zone = row[5] or ''
 document_name = row[-1] or '' # pdf_name from JOIN

 # Determine LEP name from document name (more reliable)
 lep_name = 'Inner West LEP 2022'
 if 'Ashfield' in document_name:
 lep_name = 'Ashfield LEP 2013'
 elif 'Leichhardt' in document_name:
 lep_name = 'Leichhardt LEP 2013'
 elif 'Marrickville' in document_name:
 lep_name = 'Marrickville LEP 2011'
 elif 'Inner West' in document_name:
 lep_name = 'Inner West LEP 2022'

 # Determine provision category from text content
 category = 'general'
 text_lower = provision_text.lower()
 if 'permitted without consent' in text_lower:
 category = 'permitted'
 elif 'permitted with consent' in text_lower:
 category = 'consent'
 elif 'prohibited' in text_lower or 'not permitted' in text_lower:
 category = 'prohibited'
 elif 'objectives' in text_lower and 'zone' in text_lower:
 category = 'objectives'
 elif 'minimum' in text_lower or 'maximum' in text_lower:
 category = 'standards'

 cursor.execute(insert_sql, (
 row[0], # original_provision_id
 lep_name, # lep_name
 zone, # lep_zone
 category, # provision_category
 row[6] or '', # development_type
 row[4], # provision_text
 row[3], # ref_number
 row[7], # page_number
 row[8], # section_header
 row[13] or 0.8 # classification_confidence
 ))

 lep_insertions += 1

 self.conn.commit()

 self.restructuring_report['extraction_results']['lep_provisions'] = {
 'candidates_found': len(all_candidates),
 'records_extracted': lep_insertions,
 'extraction_success': lep_insertions > 0
 }

 self.restructuring_report['total_lep_extracted'] = lep_insertions

 print(f"SUCCESS Extracted {lep_insertions:,} LEP provisions")

 def create_summary_views(self):
 """Create helpful views for Priority2Fix PRPs"""
 cursor = self.conn.cursor()

 # SEPP summary view
 sepp_view = '''
 CREATE OR REPLACE VIEW sepp_summary AS
 SELECT
 sepp_type,
 provision_category,
 COUNT(*) as provision_count,
 COUNT(DISTINCT development_type) as development_types,
 AVG(classification_confidence) as avg_confidence
 FROM sepp_provisions
 GROUP BY sepp_type, provision_category
 ORDER BY sepp_type, provision_category
 '''

 # LEP summary view
 lep_view = '''
 CREATE OR REPLACE VIEW lep_summary AS
 SELECT
 lep_name,
 lep_zone,
 provision_category,
 COUNT(*) as provision_count,
 COUNT(DISTINCT development_type) as development_types
 FROM lep_provisions
 GROUP BY lep_name, lep_zone, provision_category
 ORDER BY lep_name, lep_zone, provision_category
 '''

 cursor.execute(sepp_view)
 cursor.execute(lep_view)
 self.conn.commit()

 print("SUCCESS Created summary views for analysis")

 def execute_restructuring(self):
 """Execute complete SEPP/LEP restructuring"""
 try:
 print("=== PRP-M2: SEPP/LEP RESTRUCTURING ===")

 # Create tables
 self.create_sepp_provisions_table()
 self.create_lep_provisions_table()

 # Extract data
 self.extract_sepp_provisions()
 self.extract_lep_provisions()

 # Create analysis views
 self.create_summary_views()

 self.restructuring_report['status'] = 'COMPLETED'
 self.restructuring_report['end_time'] = datetime.now().isoformat()

 # Save report
 with open('prp_m2_restructuring_report.json', 'w') as f:
 json.dump(self.restructuring_report, f, indent=2)

 print(f"\nSUCCESS PRP-M2 COMPLETED")
 print(f" SEPP provisions: {self.restructuring_report['total_sepp_extracted']:,}")
 print(f" LEP provisions: {self.restructuring_report['total_lep_extracted']:,}")
 print(f"Report saved: prp_m2_restructuring_report.json")

 except Exception as e:
 self.restructuring_report['status'] = 'FAILED'
 self.restructuring_report['error'] = str(e)
 print(f"FAILED PRP-M2 FAILED: {e}")
 raise

 finally:
 self.conn.close()

if __name__ == "__main__":
 restructurer = PRP_M2_Restructuring()
 restructurer.execute_restructuring()