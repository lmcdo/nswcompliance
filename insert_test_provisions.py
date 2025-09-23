#!/usr/bin/env python3
"""
Insert test provisions manually for PRP-8B API testing
"""

import psycopg2
import json
from datetime import datetime

def insert_test_provisions():
 conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning",
 user="postgres",
 password="postgres"
 )
 
 test_provisions = [
 {
 'document_type': 'LEP',
 'document_name': 'Inner West LEP 2022', 
 'clause_reference': '4.1.1',
 'authority_level': 2,
 'provision_text': 'The height of a building must not exceed 8.5 metres in Zone R2',
 'provision_type': 'height',
 'applicable_zones': ['R2'],
 'numeric_value': 8.5,
 'unit': 'm',
 'measurement_context': 'maximum building height',
 'extraction_confidence': 0.95
 },
 {
 'document_type': 'DCP',
 'document_name': 'Marrickville DCP 2011',
 'clause_reference': '2.3.1',
 'authority_level': 3,
 'provision_text': 'Front setback must be minimum 6 metres in Zone R2',
 'provision_type': 'setback',
 'applicable_zones': ['R2'],
 'numeric_value': 6.0,
 'unit': 'm',
 'measurement_context': 'minimum front setback',
 'extraction_confidence': 0.90
 },
 {
 'document_type': 'SEPP',
 'document_name': 'SEPP Housing 2021',
 'clause_reference': '3.2',
 'authority_level': 1,
 'provision_text': 'Dual occupancy permitted in Zone R2 with consent',
 'provision_type': 'land_use',
 'applicable_zones': ['R2'],
 'extraction_confidence': 0.98
 }
 ]
 
 cur = conn.cursor()
 
 for i, prov in enumerate(test_provisions):
 try:
 # Insert provision
 cur.execute("""
 INSERT INTO authoritative.planning_provisions (
 document_type, document_name, clause_reference, authority_level,
 provision_text, provision_type, applicable_zones, numeric_value,
 unit, measurement_context, original_json, extraction_method,
 extraction_confidence, created_at
 ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
 RETURNING id
 """, (
 prov['document_type'],
 prov['document_name'],
 prov['clause_reference'],
 prov['authority_level'],
 prov['provision_text'],
 prov['provision_type'],
 prov['applicable_zones'],
 prov.get('numeric_value'),
 prov.get('unit'),
 prov.get('measurement_context'),
 json.dumps({'test_provision': True, 'index': i}),
 'manual_test_insert',
 prov['extraction_confidence'],
 datetime.now()
 ))
 
 provision_id = cur.fetchone()[0]
 
 # Insert authority tier
 tier_level = 1 if prov['authority_level'] == 1 and prov['extraction_confidence'] >= 0.95 else 2
 tier_name = 'fully_authoritative' if tier_level == 1 else 'high_authority'
 
 cur.execute("""
 INSERT INTO authoritative.provision_authority_tiers (
 provision_id, tier_level, tier_name, confidence_level
 ) VALUES (%s, %s, %s, %s)
 """, (
 provision_id,
 tier_level,
 tier_name,
 prov['extraction_confidence']
 ))
 
 conn.commit()
 print(f"Inserted test provision {i+1}: {prov['clause_reference']} ({tier_name})")
 
 except Exception as e:
 print(f"Error inserting provision {i+1}: {e}")
 conn.rollback()
 
 # Check final counts
 cur.execute('SELECT COUNT(*) FROM authoritative.planning_provisions')
 prov_count = cur.fetchone()[0]
 
 cur.execute('SELECT COUNT(*) FROM authoritative.provision_authority_tiers')
 tier_count = cur.fetchone()[0]
 
 print(f"\nFinal test data: {prov_count} provisions, {tier_count} tiers")
 
 conn.close()

if __name__ == "__main__":
 insert_test_provisions()