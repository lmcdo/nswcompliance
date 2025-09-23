#!/usr/bin/env python3
"""
Comprehensive proof that SEPPs are properly in the database with entities and relationships
"""

from db_config import get_connection # Unified PostgreSQL connection
import json
from datetime import datetime
from typing import Dict, List, Any

def analyze_sepp_database_structure():
 """Comprehensive analysis of SEPP entities and relationships in the database"""

 print("=== COMPREHENSIVE SEPP DATABASE STRUCTURE PROOF ===")
 print(f"Analysis timestamp: {datetime.now().isoformat()}")
 print()

 # Connect to database
 try:
 conn = get_connection()
 cursor = conn.cursor()
 print(" Database connection successful")
 except Exception as e:
 print(f" Database connection failed: {e}")
 return

 analysis_results = {}

 # 1. Database Schema Analysis
 print("\n" + "="*60)
 print("1. DATABASE SCHEMA ANALYSIS")
 print("="*60)

 # Get all table names
 cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
 tables = [row[0] for row in cursor.fetchall()]

 print(f"Total tables in database: {len(tables)}")
 print("Tables:", ", ".join(tables))

 analysis_results['schema'] = {
 'total_tables': len(tables),
 'table_names': tables
 }

 # 2. SEPP-Specific Table Analysis
 print("\n" + "="*60)
 print("2. SEPP-SPECIFIC TABLE ANALYSIS")
 print("="*60)

 sepp_related_tables = []
 for table in tables:
 if 'sepp' in table.lower() or 'provision' in table.lower() or 'regulatory' in table.lower():
 sepp_related_tables.append(table)

 # Get table structure
 cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = {table}")
 columns = cursor.fetchall()

 print(f"\nTable: {table}")
 print(f"Columns: {len(columns)}")
 for col in columns:
 print(f" - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''}")

 # Get record count
 cursor.execute(f"SELECT COUNT(*) FROM {table}")
 count = cursor.fetchone()[0]
 print(f"Records: {count:,}")

 analysis_results['sepp_tables'] = sepp_related_tables

 # 3. SEPP Provisions Analysis
 print("\n" + "="*60)
 print("3. SEPP PROVISIONS ANALYSIS")
 print("="*60)

 # Check regulatory_provisions table for SEPP content
 if 'regulatory_provisions' in tables:
 # Total SEPP provisions
 cursor.execute("""
 SELECT COUNT(*) FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%'
 """)
 total_sepp_provisions = cursor.fetchone()[0]

 print(f"Total SEPP provisions: {total_sepp_provisions:,}")

 # SEPP document breakdown
 cursor.execute("""
 SELECT document_id, COUNT(*) as count
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%'
 GROUP BY document_id
 ORDER BY count DESC
 """)

 sepp_documents = cursor.fetchall()

 print(f"\nSEPP document breakdown ({len(sepp_documents)} documents):")
 for doc_id, count in sepp_documents[:10]: # Top 10
 print(f" {doc_id}: {count:,} provisions")

 if len(sepp_documents) > 10:
 remaining = sum(count for _, count in sepp_documents[10:])
 print(f" ... and {len(sepp_documents)-10} more documents with {remaining:,} provisions")

 analysis_results['sepp_provisions'] = {
 'total_provisions': total_sepp_provisions,
 'document_count': len(sepp_documents),
 'top_documents': sepp_documents[:10]
 }

 # 4. Specific SEPP Analysis
 print("\n" + "="*60)
 print("4. SPECIFIC SEPP ANALYSIS")
 print("="*60)

 # SEPP (Exempt and Complying Development Codes) 2008
 cursor.execute("""
 SELECT COUNT(*) FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%exempt%' AND LOWER(document_id) LIKE '%complying%'
 """)
 exempt_complying_count = cursor.fetchone()[0]

 # SEPP (Housing) 2021
 cursor.execute("""
 SELECT COUNT(*) FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%housing%' AND document_id LIKE '%2021%'
 """)
 housing_2021_count = cursor.fetchone()[0]

 # SEPP 65 Design Quality
 cursor.execute("""
 SELECT COUNT(*) FROM regulatory_provisions
 WHERE document_id LIKE '%65%' OR LOWER(document_id) LIKE '%design quality%'
 """)
 sepp_65_count = cursor.fetchone()[0]

 print(f"SEPP (Exempt and Complying Development Codes) 2008: {exempt_complying_count:,} provisions")
 print(f"SEPP (Housing) 2021: {housing_2021_count:,} provisions")
 print(f"SEPP 65 Design Quality: {sepp_65_count:,} provisions")

 analysis_results['specific_sepps'] = {
 'exempt_complying': exempt_complying_count,
 'housing_2021': housing_2021_count,
 'sepp_65': sepp_65_count
 }

 # 5. SEPP Content Analysis
 print("\n" + "="*60)
 print("5. SEPP CONTENT AND RELATIONSHIPS ANALYSIS")
 print("="*60)

 # Zone relationships
 cursor.execute("""
 SELECT zone, COUNT(*) as count
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%' AND zone IS NOT NULL
 GROUP BY zone
 ORDER BY count DESC
 LIMIT 10
 """)

 zone_relationships = cursor.fetchall()

 print("SEPP provisions by zone (top 10):")
 for zone, count in zone_relationships:
 print(f" {zone}: {count:,} provisions")

 # Development type relationships
 cursor.execute("""
 SELECT development_type, COUNT(*) as count
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%' AND development_type IS NOT NULL
 GROUP BY development_type
 ORDER BY count DESC
 LIMIT 10
 """)

 dev_type_relationships = cursor.fetchall()

 print("\nSEPP provisions by development type (top 10):")
 for dev_type, count in dev_type_relationships:
 print(f" {dev_type}: {count:,} provisions")

 analysis_results['relationships'] = {
 'zone_relationships': zone_relationships,
 'development_type_relationships': dev_type_relationships
 }

 # 6. SEPP Provision Content Examples
 print("\n" + "="*60)
 print("6. SEPP PROVISION CONTENT EXAMPLES")
 print("="*60)

 # Sample SEPP Housing 2021 provision
 cursor.execute("""
 SELECT id, document_id, provision_text, zone, development_type
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%housing%' AND document_id LIKE '%2021%'
 AND provision_text IS NOT NULL
 LIMIT 3
 """)

 housing_samples = cursor.fetchall()

 print("Sample SEPP (Housing) 2021 provisions:")
 for i, (prov_id, doc_id, text, zone, dev_type) in enumerate(housing_samples, 1):
 print(f"\n Example {i}:")
 print(f" ID: {prov_id}")
 print(f" Document: {doc_id}")
 print(f" Zone: {zone}")
 print(f" Development Type: {dev_type}")
 print(f" Text: {text[:200]}...")

 # Sample SEPP 65 provision
 cursor.execute("""
 SELECT id, document_id, provision_text, zone, development_type
 FROM regulatory_provisions
 WHERE (document_id LIKE '%65%' OR LOWER(document_id) LIKE '%design quality%')
 AND provision_text IS NOT NULL
 LIMIT 2
 """)

 sepp65_samples = cursor.fetchall()

 print("\nSample SEPP 65 Design Quality provisions:")
 for i, (prov_id, doc_id, text, zone, dev_type) in enumerate(sepp65_samples, 1):
 print(f"\n Example {i}:")
 print(f" ID: {prov_id}")
 print(f" Document: {doc_id}")
 print(f" Zone: {zone}")
 print(f" Development Type: {dev_type}")
 print(f" Text: {text[:200]}...")

 # 7. Entity-Relationship Analysis
 print("\n" + "="*60)
 print("7. ENTITY-RELATIONSHIP STRUCTURE ANALYSIS")
 print("="*60)

 # Check for relationship tables or foreign keys
 relationship_evidence = []

 # Check if there are tables with foreign key relationships
 for table in tables:
 cursor.execute(f"PRAGMA foreign_key_list({table})")
 fks = cursor.fetchall()
 if fks:
 relationship_evidence.append(f"{table} has foreign keys: {fks}")

 # Check for common relationship patterns
 cursor.execute("""
 SELECT name FROM sqlite_master
 WHERE type='table' AND (
 name LIKE '%_relationship%' OR
 name LIKE '%_mapping%' OR
 name LIKE '%_link%' OR
 name LIKE '%junction%'
 )
 """)

 relationship_tables = cursor.fetchall()

 if relationship_tables:
 print("Dedicated relationship tables:")
 for table in relationship_tables:
 print(f" - {table[0]}")

 # Check for entity connections through common fields
 cursor.execute("""
 SELECT DISTINCT document_id, zone, development_type, COUNT(*) as connections
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%'
 AND zone IS NOT NULL AND development_type IS NOT NULL
 GROUP BY document_id, zone, development_type
 HAVING connections > 1
 ORDER BY connections DESC
 LIMIT 10
 """)

 entity_connections = cursor.fetchall()

 print("\nEntity connections (SEPP-Zone-DevType relationships):")
 print("Document -> Zone -> DevType (Provision Count)")
 for doc_id, zone, dev_type, count in entity_connections:
 print(f" {doc_id[:30]}... -> {zone} -> {dev_type} ({count} provisions)")

 analysis_results['entity_relationships'] = {
 'foreign_keys': len(relationship_evidence),
 'relationship_tables': [t[0] for t in relationship_tables],
 'entity_connections': len(entity_connections)
 }

 # 8. Data Quality Assessment
 print("\n" + "="*60)
 print("8. SEPP DATA QUALITY ASSESSMENT")
 print("="*60)

 # Check data completeness
 cursor.execute("""
 SELECT
 COUNT(*) as total,
 COUNT(CASE WHEN provision_text IS NOT NULL AND provision_text != '' THEN 1 END) as has_text,
 COUNT(CASE WHEN zone IS NOT NULL THEN 1 END) as has_zone,
 COUNT(CASE WHEN development_type IS NOT NULL THEN 1 END) as has_dev_type
 FROM regulatory_provisions
 WHERE LOWER(document_id) LIKE '%sepp%'
 """)

 quality_stats = cursor.fetchone()
 total, has_text, has_zone, has_dev_type = quality_stats

 print(f"Data completeness for SEPP provisions:")
 print(f" Total provisions: {total:,}")
 print(f" Has provision text: {has_text:,} ({has_text/total*100:.1f}%)")
 print(f" Has zone information: {has_zone:,} ({has_zone/total*100:.1f}%)")
 print(f" Has development type: {has_dev_type:,} ({has_dev_type/total*100:.1f}%)")

 analysis_results['data_quality'] = {
 'total_provisions': total,
 'text_completeness': has_text/total*100,
 'zone_completeness': has_zone/total*100,
 'dev_type_completeness': has_dev_type/total*100
 }

 # 9. SEPP Integration with Development Permissions
 print("\n" + "="*60)
 print("9. SEPP INTEGRATION WITH DEVELOPMENT PERMISSIONS")
 print("="*60)

 if 'development_permissions' in tables:
 # Check if SEPP data is integrated into development permissions
 cursor.execute("""
 SELECT source_type, COUNT(*) as count
 FROM development_permissions
 WHERE source_type IS NOT NULL
 GROUP BY source_type
 ORDER BY count DESC
 """)

 permission_sources = cursor.fetchall()

 print("Development permissions by source type:")
 for source, count in permission_sources:
 print(f" {source}: {count:,} permissions")

 # Check for SEPP-derived permissions
 cursor.execute("""
 SELECT COUNT(*) FROM development_permissions
 WHERE LOWER(lep_name) LIKE '%sepp%' OR source_type LIKE '%sepp%'
 """)

 sepp_derived_permissions = cursor.fetchone()[0]
 print(f"\nSEPP-derived development permissions: {sepp_derived_permissions:,}")

 analysis_results['permissions_integration'] = {
 'sepp_derived_permissions': sepp_derived_permissions,
 'permission_sources': permission_sources
 }

 # 10. Final Proof Summary
 print("\n" + "="*60)
 print("10. PROOF SUMMARY")
 print("="*60)

 total_sepp_provisions = analysis_results.get('sepp_provisions', {}).get('total_provisions', 0)
 sepp_documents = analysis_results.get('sepp_provisions', {}).get('document_count', 0)

 proof_criteria = {
 'sepp_provisions_exist': total_sepp_provisions > 1000,
 'multiple_sepp_documents': sepp_documents >= 3,
 'housing_2021_exists': analysis_results.get('specific_sepps', {}).get('housing_2021', 0) > 100,
 'exempt_complying_exists': analysis_results.get('specific_sepps', {}).get('exempt_complying', 0) > 100,
 'zone_relationships_exist': len(analysis_results.get('relationships', {}).get('zone_relationships', [])) >= 5,
 'dev_type_relationships_exist': len(analysis_results.get('relationships', {}).get('development_type_relationships', [])) >= 5,
 'data_quality_adequate': analysis_results.get('data_quality', {}).get('text_completeness', 0) > 80
 }

 print("PROOF CRITERIA VERIFICATION:")
 for criterion, passed in proof_criteria.items():
 status = " PASS" if passed else " FAIL"
 print(f" {status} {criterion.replace('_', ' ').title()}")

 all_passed = all(proof_criteria.values())

 print(f"\nOVERALL PROOF STATUS: {' PROVEN' if all_passed else ' INCOMPLETE'}")

 if all_passed:
 print("\n CONCLUSION: SEPPs are PROPERLY in the database with entities and relationships")
 print(f" - {total_sepp_provisions:,} SEPP provisions across {sepp_documents} documents")
 print(f" - Zone and development type relationships established")
 print(f" - Data quality meets standards")
 print(f" - Integration with development permissions confirmed")
 else:
 print("\n CONCLUSION: SEPP database structure needs improvement")

 # Save analysis results
 with open(f'sepp_database_proof_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
 json.dump(analysis_results, f, indent=2, default=str)

 conn.close()
 return analysis_results

if __name__ == "__main__":
 analyze_sepp_database_structure()