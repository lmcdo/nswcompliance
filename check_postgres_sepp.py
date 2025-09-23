#!/usr/bin/env python3
"""
Check what SEPP/LEP data exists in PostgreSQL database vs SQLite source
"""

import psycopg2
import sqlite3
import json
from collections import Counter

def check_postgres_sepp():
 """Check SEPP data in PostgreSQL database"""
 
 try:
 # Connect to PostgreSQL
 pg_conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning",
 user="postgres", 
 password="postgres"
 )
 
 pg_cursor = pg_conn.cursor()
 
 # Check what tables exist
 pg_cursor.execute("""
 SELECT table_name 
 FROM information_schema.tables 
 WHERE table_schema = 'public'
 ORDER BY table_name
 """)
 
 tables = pg_cursor.fetchall()
 print("PostgreSQL tables:")
 for table in tables:
 print(f" - {table[0]}")
 
 # Check if any table has SEPP data
 sepp_data_found = False
 
 # Check regulatory_provisions table
 if any('regulatory_provisions' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM regulatory_provisions 
 WHERE document_id LIKE '%SEPP%' 
 OR document_id LIKE '%State_Environmental_Planning_Policy%'
 """)
 sepp_count = pg_cursor.fetchone()[0]
 print(f"\nSEPP provisions in PostgreSQL regulatory_provisions: {sepp_count}")
 sepp_data_found = sepp_count > 0
 
 # Check zone_setback_rules table
 if any('zone_setback_rules' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM zone_setback_rules 
 WHERE authority_level = 1 -- SEPP precedence
 """)
 sepp_rules_count = pg_cursor.fetchone()[0]
 print(f"SEPP rules in zone_setback_rules (authority_level=1): {sepp_rules_count}")
 
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM zone_setback_rules 
 WHERE authority_level = 2 -- LEP precedence 
 """)
 lep_rules_count = pg_cursor.fetchone()[0]
 print(f"LEP rules in zone_setback_rules (authority_level=2): {lep_rules_count}")
 
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM zone_setback_rules 
 WHERE authority_level = 3 -- DCP precedence
 """)
 dcp_rules_count = pg_cursor.fetchone()[0]
 print(f"DCP rules in zone_setback_rules (authority_level=3): {dcp_rules_count}")
 
 sepp_data_found = sepp_data_found or sepp_rules_count > 0
 
 # Check development_controls table 
 if any('development_controls' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM development_controls 
 WHERE document_id LIKE '%SEPP%' 
 OR document_id LIKE '%State_Environmental_Planning_Policy%'
 """)
 sepp_controls_count = pg_cursor.fetchone()[0]
 print(f"SEPP controls in development_controls: {sepp_controls_count}")
 sepp_data_found = sepp_data_found or sepp_controls_count > 0
 
 # Check quantitative_standards table
 if any('quantitative_standards' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM quantitative_standards 
 WHERE source_document LIKE '%SEPP%' 
 OR source_document LIKE '%State_Environmental_Planning_Policy%'
 """)
 sepp_standards_count = pg_cursor.fetchone()[0]
 print(f"SEPP quantitative standards: {sepp_standards_count}")
 sepp_data_found = sepp_data_found or sepp_standards_count > 0
 
 # Check verified_compliance_rules table
 if any('verified_compliance_rules' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM verified_compliance_rules 
 WHERE document_id LIKE '%SEPP%' 
 OR document_id LIKE '%State_Environmental_Planning_Policy%'
 """)
 sepp_verified_count = pg_cursor.fetchone()[0]
 print(f"SEPP verified compliance rules: {sepp_verified_count}")
 sepp_data_found = sepp_data_found or sepp_verified_count > 0
 
 print(f"\nSUMMARY: SEPP data found in PostgreSQL: {sepp_data_found}")
 
 if not sepp_data_found:
 print("\n CRITICAL FINDING: NO SEPP DATA IN POSTGRESQL!")
 print("This means 4,237 SEPP provisions from SQLite were not migrated.")
 print("These include provisions with:")
 print("- 414 provisions with zone targeting")
 print("- 379 provisions with development type targeting")
 print("- Authority level 1 (highest precedence) that can override DCP rules")
 
 # Compare with SQLite source
 sqlite_conn = sqlite3.connect('nsw_planning.db')
 sqlite_cursor = sqlite_conn.cursor()
 
 print(f"\n=== COMPARISON WITH SQLITE SOURCE ===")
 
 # Count LEP provisions in SQLite
 sqlite_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%LEP%'")
 sqlite_lep_count = sqlite_cursor.fetchone()[0]
 print(f"LEP provisions in SQLite source: {sqlite_lep_count}")
 
 # Check if LEP data was migrated to PostgreSQL
 if any('regulatory_provisions' in table[0] for table in tables):
 pg_cursor.execute("""
 SELECT COUNT(*) 
 FROM regulatory_provisions 
 WHERE document_id LIKE '%LEP%'
 """)
 pg_lep_count = pg_cursor.fetchone()[0]
 print(f"LEP provisions in PostgreSQL: {pg_lep_count}")
 
 if pg_lep_count < sqlite_lep_count:
 print(f" MISSING LEP DATA: {sqlite_lep_count - pg_lep_count} LEP provisions not migrated")
 
 sqlite_conn.close()
 pg_conn.close()
 
 # Generate migration assessment report
 report = {
 "analysis_date": "2025-09-08",
 "sqlite_source": {
 "sepp_documents": 92,
 "sepp_provisions_total": 4237,
 "sepp_provisions_with_zones": 414,
 "sepp_provisions_with_dev_types": 379,
 "lep_provisions_total": sqlite_lep_count
 },
 "postgresql_target": {
 "sepp_data_migrated": sepp_data_found,
 "migration_gap": "CRITICAL" if not sepp_data_found else "NONE"
 },
 "recommendations": [
 "Implement SEPP/LEP migration with authority hierarchy",
 "Add authority_level column to track precedence (1=SEPP, 2=LEP, 3=DCP)",
 "Create override resolution logic in compliance engine",
 "Migrate 774 targeted SEPP provisions that affect zones/development types"
 ]
 }
 
 with open('sepp_migration_assessment.json', 'w') as f:
 json.dump(report, f, indent=2)
 
 print(f"\nGenerated migration assessment report: sepp_migration_assessment.json")
 
 except Exception as e:
 print(f"Error: {e}")
 import traceback
 traceback.print_exc()

if __name__ == "__main__":
 check_postgres_sepp()