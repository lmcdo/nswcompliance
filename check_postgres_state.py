#!/usr/bin/env python3
"""
Check current PostgreSQL database state
"""

from db_config import get_connection

def check_database_state():
 try:
 conn = get_connection()
 cursor = conn.cursor()

 print('=== CURRENT POSTGRESQL DATABASE STATE ===')

 tables = [
 'regulatory_provisions',
 'development_controls',
 'quantitative_standards',
 'sepp_provisions',
 'lep_provisions',
 'development_permissions',
 'documents'
 ]

 for table in tables:
 try:
 cursor.execute(f'SELECT COUNT(*) FROM {table}')
 count = cursor.fetchone()[0]
 print(f'{table}: {count:,} records')
 except Exception as e:
 print(f'{table}: ERROR - {e}')

 print('\n=== BASIX AND SPECIAL PROVISIONS ANALYSIS ===')

 # Check for existing BASIX-related data
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text ILIKE '%basix%'")
 basix_mentions = cursor.fetchone()[0]
 print(f'BASIX mentions in provisions: {basix_mentions}')

 # Check climate zone data
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text ILIKE '%climate%zone%'")
 climate_mentions = cursor.fetchone()[0]
 print(f'Climate zone mentions: {climate_mentions}')

 # Check for flood planning
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text ILIKE '%flood%'")
 flood_mentions = cursor.fetchone()[0]
 print(f'Flood planning mentions: {flood_mentions}')

 # Check for bushfire
 cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text ILIKE '%bushfire%'")
 bushfire_mentions = cursor.fetchone()[0]
 print(f'Bushfire mentions: {bushfire_mentions}')

 print('\n=== ZONES COVERAGE ===')
 # Check zones coverage
 cursor.execute('SELECT zone, COUNT(*) FROM regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY COUNT(*) DESC LIMIT 10')
 zones = cursor.fetchall()
 for zone, count in zones:
 print(f' {zone}: {count:,} provisions')

 print('\n=== DOCUMENT TYPES ===')
 # Check document types
 cursor.execute('SELECT document_type, COUNT(*) FROM documents GROUP BY document_type ORDER BY COUNT(*) DESC')
 doc_types = cursor.fetchall()
 for doc_type, count in doc_types:
 print(f' {doc_type}: {count:,} documents')

 print('\n=== SEPP/LEP BREAKDOWN ===')
 # Check SEPP provisions by document
 cursor.execute('SELECT COUNT(*) FROM sepp_provisions')
 sepp_count = cursor.fetchone()[0]
 print(f'SEPP provisions: {sepp_count:,}')

 # Check LEP provisions
 cursor.execute('SELECT COUNT(*) FROM lep_provisions')
 lep_count = cursor.fetchone()[0]
 print(f'LEP provisions: {lep_count:,}')

 print('\n=== EXISTING SPECIAL TABLES CHECK ===')
 # Check if BASIX or special provisions tables already exist
 special_tables = ['basix_provisions', 'special_provisions_registry', 'provision_thresholds']

 for table in special_tables:
 cursor.execute("""
 SELECT EXISTS (
 SELECT FROM information_schema.tables
 WHERE table_name = %s
 )
 """, (table,))
 exists = cursor.fetchone()[0]

 if exists:
 cursor.execute(f'SELECT COUNT(*) FROM {table}')
 count = cursor.fetchone()[0]
 print(f' {table}: EXISTS with {count:,} records')
 else:
 print(f' {table}: NOT EXISTS')

 conn.close()

 except Exception as e:
 print(f"Database check failed: {e}")

if __name__ == "__main__":
 check_database_state()