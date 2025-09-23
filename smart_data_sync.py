"""
SMART DATA SYNC: SQLite -> PostgreSQL
=====================================
The simplest, smartest way to sync missing data and relationships
"""

import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime

class SmartDataSync:
 def __init__(self):
 self.sqlite_conn = sqlite3.connect('nsw_planning.db')
 self.sqlite_conn.row_factory = sqlite3.Row
 
 self.pg_conn = psycopg2.connect(
 host='localhost', port=5432, database='nsw_planning',
 user='postgres', password='postgres',
 cursor_factory=psycopg2.extras.RealDictCursor
 )
 
 def sync_missing_zones(self):
 """Copy missing zones from SQLite to PostgreSQL"""
 print("1. SYNCING MISSING ZONES")
 print("="*40)
 
 # Missing zones: C1, C2, C3, C5, C7, C8, C9, E2, O1, R5
 missing_zones = ['C1', 'C2', 'C3', 'C5', 'C7', 'C8', 'C9', 'E2', 'O1', 'R5']
 
 sqlite_cursor = self.sqlite_conn.cursor()
 pg_cursor = self.pg_conn.cursor()
 
 total_copied = 0
 
 for zone in missing_zones:
 # Get all provisions for this zone from SQLite
 provisions = sqlite_cursor.execute('''
 SELECT document_id, provision_type, ref_number, provision_text,
 zone, development_type, page_number, section_header,
 text_level, domain_classification, classification_confidence,
 cross_contamination_checked, prp_k1_enhanced
 FROM regulatory_provisions 
 WHERE zone = ?
 ''', (zone,)).fetchall()
 
 if not provisions:
 print(f" {zone}: No provisions found")
 continue
 
 copied = 0
 for prov in provisions:
 # Check if already exists in PostgreSQL
 pg_cursor.execute('''
 SELECT id FROM regulatory_provisions
 WHERE document_id = %s AND ref_number = %s 
 AND provision_text = %s LIMIT 1
 ''', (prov['document_id'], prov['ref_number'], prov['provision_text']))
 
 if pg_cursor.fetchone():
 continue # Skip duplicates
 
 # Insert new provision
 pg_cursor.execute('''
 INSERT INTO regulatory_provisions (
 document_id, provision_type, ref_number, provision_text,
 zone, development_type, page_number, section_header,
 text_level, domain_classification, classification_confidence,
 cross_contamination_checked, prp_k1_enhanced, created_at
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 ''', (
 prov['document_id'], prov['provision_type'], prov['ref_number'],
 prov['provision_text'], prov['zone'], prov['development_type'],
 prov['page_number'], prov['section_header'], prov['text_level'],
 prov['domain_classification'], prov['classification_confidence'],
 bool(prov['cross_contamination_checked']), bool(prov['prp_k1_enhanced']),
 datetime.now()
 ))
 copied += 1
 
 total_copied += copied
 print(f" {zone}: Copied {copied} provisions")
 
 self.pg_conn.commit()
 print(f"TOTAL: Copied {total_copied} provisions for missing zones")
 
 def fix_zone_assignments(self):
 """Fix NULL zone assignments in PostgreSQL using SQLite as reference"""
 print("\n2. FIXING ZONE ASSIGNMENTS")
 print("="*40)
 
 sqlite_cursor = self.sqlite_conn.cursor()
 pg_cursor = self.pg_conn.cursor()
 
 # Get provisions with proper zone assignments from SQLite
 sqlite_zones = sqlite_cursor.execute('''
 SELECT document_id, ref_number, provision_text, zone
 FROM regulatory_provisions
 WHERE zone IS NOT NULL 
 AND ref_number IS NOT NULL
 AND ref_number != ''
 ''').fetchall()
 
 fixed = 0
 for row in sqlite_zones:
 # Update matching provisions in PostgreSQL that have NULL zones
 result = pg_cursor.execute('''
 UPDATE regulatory_provisions
 SET zone = %s
 WHERE zone IS NULL
 AND document_id = %s
 AND ref_number = %s
 AND provision_text = %s
 ''', (row['zone'], row['document_id'], row['ref_number'], row['provision_text']))
 
 if pg_cursor.rowcount > 0:
 fixed += pg_cursor.rowcount
 
 self.pg_conn.commit()
 print(f"FIXED: {fixed} NULL zone assignments")
 
 def sync_quantitative_standards(self):
 """Sync missing quantitative standards with proper ID mapping"""
 print("\n3. SYNCING QUANTITATIVE STANDARDS")
 print("="*40)
 
 sqlite_cursor = self.sqlite_conn.cursor()
 pg_cursor = self.pg_conn.cursor()
 
 # Get all quantitative standards from SQLite with provision details
 sqlite_standards = sqlite_cursor.execute('''
 SELECT qs.provision_id as sqlite_prov_id, qs.numeric_value, qs.unit,
 qs.qualifier, qs.context, qs.confidence_score, qs.raw_text,
 rp.document_id, rp.ref_number, rp.provision_text
 FROM quantitative_standards qs
 JOIN regulatory_provisions rp ON qs.provision_id = rp.id
 WHERE qs.context LIKE '%setback%'
 ''').fetchall()
 
 created = 0
 for std in sqlite_standards:
 # Find matching provision in PostgreSQL
 pg_cursor.execute('''
 SELECT id FROM regulatory_provisions
 WHERE document_id = %s 
 AND ref_number = %s
 AND provision_text = %s
 LIMIT 1
 ''', (std['document_id'], std['ref_number'], std['provision_text']))
 
 pg_prov_row = pg_cursor.fetchone()
 if not pg_prov_row:
 continue # Skip if no matching provision
 
 pg_prov_id = pg_prov_row['id']
 
 # Check if standard already exists
 pg_cursor.execute('''
 SELECT id FROM quantitative_standards
 WHERE provision_id = %s 
 AND context = %s
 AND numeric_value = %s
 ''', (pg_prov_id, std['context'], std['numeric_value']))
 
 if pg_cursor.fetchone():
 continue # Skip duplicates
 
 # Create the quantitative standard
 pg_cursor.execute('''
 INSERT INTO quantitative_standards (
 provision_id, numeric_value, unit, qualifier, context,
 confidence_score, raw_text, created_timestamp
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
 ''', (
 pg_prov_id, std['numeric_value'], std['unit'], std['qualifier'],
 std['context'], std['confidence_score'], std['raw_text'], 
 datetime.now()
 ))
 created += 1
 
 self.pg_conn.commit()
 print(f"CREATED: {created} new quantitative standards")
 
 def verify_sync(self):
 """Verify that the sync worked"""
 print("\n4. VERIFICATION")
 print("="*40)
 
 pg_cursor = self.pg_conn.cursor()
 
 # Check zone coverage
 pg_cursor.execute('''
 SELECT zone, COUNT(*) as provisions,
 COUNT(DISTINCT development_type) as dev_types
 FROM regulatory_provisions
 WHERE zone IS NOT NULL
 GROUP BY zone
 ORDER BY zone
 ''')
 zone_data = pg_cursor.fetchall()
 
 print(f"PostgreSQL now has {len(zone_data)} zones with provisions:")
 for row in zone_data:
 print(f" {row['zone']}: {row['provisions']} provisions, {row['dev_types']} dev types")
 
 # Check quantitative standards
 pg_cursor.execute('''
 SELECT rp.zone, rp.development_type, COUNT(qs.id) as standards
 FROM regulatory_provisions rp
 JOIN quantitative_standards qs ON rp.id = qs.provision_id
 WHERE rp.zone IS NOT NULL 
 AND qs.context LIKE '%setback%'
 GROUP BY rp.zone, rp.development_type
 ORDER BY rp.zone, rp.development_type
 ''')
 standards_data = pg_cursor.fetchall()
 
 print(f"\nLinked setback standards:")
 for row in standards_data:
 print(f" {row['zone']} {row['development_type']}: {row['standards']} standards")
 
 def run_complete_sync(self):
 """Run the complete sync process"""
 print("SMART DATA SYNC: SQLite -> PostgreSQL")
 print("="*60)
 print("Syncing missing zones, fixing assignments, and linking standards...")
 
 try:
 self.sync_missing_zones()
 self.fix_zone_assignments() 
 self.sync_quantitative_standards()
 self.verify_sync()
 
 print("\nSUCCESS: Data sync completed!")
 print("PostgreSQL now has proper zone coverage and quantitative standards")
 
 except Exception as e:
 print(f"ERROR: Sync failed - {e}")
 self.pg_conn.rollback()
 raise
 finally:
 self.sqlite_conn.close()
 self.pg_conn.close()

if __name__ == "__main__":
 syncer = SmartDataSync()
 syncer.run_complete_sync()