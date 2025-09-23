#!/usr/bin/env python3
"""
Analyze the clause text content and linking structure for Referenced Legislation accordion feature
"""
import sqlite3
import json
from typing import Dict, Any

def analyze_database_schema():
 """Analyze the database schema for regulatory content"""
 print("=== DATABASE SCHEMA ANALYSIS ===\n")
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Get all tables
 cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
 tables = [row[0] for row in cur.fetchall()]
 
 print(f"Available tables: {len(tables)}")
 for table in tables:
 print(f" - {table}")
 
 print("\n=== REGULATORY_PROVISIONS TABLE STRUCTURE ===")
 if 'regulatory_provisions' in tables:
 cur.execute("PRAGMA table_info(regulatory_provisions)")
 columns = cur.fetchall()
 print("Columns:")
 for col in columns:
 print(f" {col[1]:<25} {col[2]:<15} {'NOT NULL' if col[3] else 'NULLABLE'}")
 
 # Get sample data
 print("\n=== SAMPLE REGULATORY PROVISIONS ===")
 cur.execute("""
 SELECT rp.id, rp.document_id, d.title as document_title, rp.provision_type, rp.ref_number, 
 LENGTH(rp.provision_text) as text_length, rp.page_number, rp.section_header
 FROM regulatory_provisions rp
 LEFT JOIN documents d ON rp.document_id = d.id
 LIMIT 5
 """)
 
 for row in cur.fetchall():
 print(f"ID: {row[0]}")
 print(f" Document: {row[2] or 'Unknown'} ({row[1]})")
 print(f" Type: {row[3]}")
 print(f" Ref Number: {row[4]}")
 print(f" Text Length: {row[5]} chars")
 print(f" Page: {row[6]}")
 print(f" Section: {row[7]}")
 print("---")
 else:
 print("regulatory_provisions table not found!")
 
 print("\n=== DEVELOPMENT_CONTROLS TABLE STRUCTURE ===")
 if 'development_controls' in tables:
 cur.execute("PRAGMA table_info(development_controls)")
 columns = cur.fetchall()
 print("Columns:")
 for col in columns:
 print(f" {col[1]:<25} {col[2]:<15} {'NOT NULL' if col[3] else 'NULLABLE'}")
 
 # Get sample setback controls
 print("\n=== SAMPLE SETBACK CONTROLS ===")
 cur.execute("""
 SELECT dc.id, dc.control_type, dc.control_subtype, dc.value_numeric, 
 dc.value_text, dc.provision_id, rp.ref_number, d.title as document_title
 FROM development_controls dc
 LEFT JOIN regulatory_provisions rp ON dc.provision_id = rp.id
 LEFT JOIN documents d ON rp.document_id = d.id
 WHERE dc.control_type = 'setback'
 LIMIT 5
 """)
 
 for row in cur.fetchall():
 print(f"Control ID: {row[0]}")
 print(f" Type: {row[1]} - {row[2]}")
 print(f" Value: {row[3]} ({row[4]})")
 print(f" Links to Provision: {row[5]} - {row[6]} ({row[7]})")
 print("---")
 else:
 print("development_controls table not found!")
 
 conn.close()

def analyze_clause_text_content():
 """Check the quality and completeness of clause text content"""
 print("\n=== CLAUSE TEXT CONTENT ANALYSIS ===\n")
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Check text content statistics
 cur.execute("""
 SELECT 
 COUNT(*) as total_provisions,
 COUNT(provision_text) as has_text,
 AVG(LENGTH(provision_text)) as avg_text_length,
 MIN(LENGTH(provision_text)) as min_text_length,
 MAX(LENGTH(provision_text)) as max_text_length,
 COUNT(CASE WHEN LENGTH(provision_text) > 100 THEN 1 END) as substantial_text
 FROM regulatory_provisions
 WHERE provision_text IS NOT NULL
 """)
 
 stats = cur.fetchone()
 print(f"Total provisions: {stats[0]:,}")
 print(f"Provisions with text: {stats[1]:,}")
 print(f"Average text length: {stats[2]:.1f} chars")
 print(f"Min text length: {stats[3]} chars")
 print(f"Max text length: {stats[4]:,} chars")
 print(f"Provisions with substantial text (>100 chars): {stats[5]:,}")
 
 # Check document types and hierarchy
 print("\n=== DOCUMENT HIERARCHY ===")
 cur.execute("""
 SELECT d.title as document_title, rp.provision_type, COUNT(*) as count
 FROM regulatory_provisions rp
 LEFT JOIN documents d ON rp.document_id = d.id
 GROUP BY d.title, rp.provision_type
 ORDER BY d.title, rp.provision_type
 """)
 
 current_doc = None
 for row in cur.fetchall():
 doc_title = row[0]
 if doc_title != current_doc:
 print(f"\n{doc_title}:")
 current_doc = doc_title
 print(f" {row[1]}: {row[2]:,} provisions")
 
 # Sample actual clause text for setback-related provisions
 print("\n=== SAMPLE SETBACK CLAUSE TEXT ===")
 cur.execute("""
 SELECT rp.ref_number, rp.section_header, rp.provision_text
 FROM regulatory_provisions rp
 JOIN development_controls dc ON rp.id = dc.provision_id
 WHERE dc.control_type = 'setback' AND rp.provision_text IS NOT NULL
 LIMIT 3
 """)
 
 for row in cur.fetchall():
 print(f"Clause: {row[0]}")
 print(f"Section: {row[1]}")
 print(f"Text: {row[2][:300]}...")
 print("---")
 
 conn.close()

def analyze_current_api_response():
 """Check what clause information is currently available in API responses"""
 print("\n=== CURRENT API RESPONSE STRUCTURE ===\n")
 
 # Import and test the database calculator
 from database_setback_calculator import DatabaseSetbackCalculator
 
 class MockProperty:
 def __init__(self):
 self.zone = 'R2'
 self.address = '34 Pile Street, Dulwich Hill'
 
 calc = DatabaseSetbackCalculator()
 property_data = MockProperty()
 
 setbacks = calc.get_setbacks_for_property(property_data)
 
 print("Current setback response includes:")
 for position, data in setbacks.items():
 print(f"\n{position.upper()} SETBACK:")
 for key, value in data.items():
 print(f" {key}: {value}")
 
 # Check if we have provision text in the response
 has_full_text = any('text' in data for data in setbacks.values())
 print(f"\nIncludes full clause text: {'YES' if has_full_text else 'NO'}")

def analyze_linking_structure():
 """Analyze how setback calculations link to specific clauses"""
 print("\n=== CLAUSE LINKING ANALYSIS ===\n")
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Check the join relationship between development_controls and regulatory_provisions
 cur.execute("""
 SELECT 
 COUNT(DISTINCT dc.id) as total_controls,
 COUNT(DISTINCT dc.provision_id) as linked_provisions,
 COUNT(DISTINCT rp.id) as valid_links
 FROM development_controls dc
 LEFT JOIN regulatory_provisions rp ON dc.provision_id = rp.id
 WHERE dc.control_type = 'setback'
 """)
 
 link_stats = cur.fetchone()
 print(f"Total setback controls: {link_stats[0]}")
 print(f"Controls with provision links: {link_stats[1]}") 
 print(f"Valid provision links: {link_stats[2]}")
 
 # Check document hierarchy for linked provisions
 cur.execute("""
 SELECT d.title as document_title, rp.provision_type, COUNT(*) as linked_controls
 FROM development_controls dc
 JOIN regulatory_provisions rp ON dc.provision_id = rp.id
 LEFT JOIN documents d ON rp.document_id = d.id
 WHERE dc.control_type = 'setback'
 GROUP BY d.title, rp.provision_type
 ORDER BY linked_controls DESC
 """)
 
 print("\nLinked provisions by document:")
 for row in cur.fetchall():
 print(f" {row[0]} ({row[1]}): {row[2]} linked controls")
 
 conn.close()

def assess_accordion_readiness():
 """Assess what's needed for Referenced Legislation accordion implementation"""
 print("\n=== ACCORDION FEATURE READINESS ASSESSMENT ===\n")
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Check if we have the necessary data components
 requirements = {
 'Full clause text': False,
 'Clause numbers/citations': False, 
 'Document hierarchy (SEPP/LEP/DCP)': False,
 'Provision-to-control linking': False,
 'Section headers': False,
 'Page references': False
 }
 
 # Check full clause text
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE LENGTH(provision_text) > 50")
 if cur.fetchone()[0] > 100:
 requirements['Full clause text'] = True
 
 # Check clause numbers
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number IS NOT NULL AND ref_number != ''")
 if cur.fetchone()[0] > 100:
 requirements['Clause numbers/citations'] = True
 
 # Check document types
 cur.execute("""
 SELECT COUNT(DISTINCT d.title) FROM regulatory_provisions rp
 JOIN documents d ON rp.document_id = d.id
 WHERE d.title LIKE '%SEPP%' OR d.title LIKE '%LEP%' OR d.title LIKE '%DCP%'
 """)
 if cur.fetchone()[0] > 0:
 requirements['Document hierarchy (SEPP/LEP/DCP)'] = True
 
 # Check linking
 cur.execute("SELECT COUNT(*) FROM development_controls WHERE provision_id IS NOT NULL")
 if cur.fetchone()[0] > 10:
 requirements['Provision-to-control linking'] = True
 
 # Check section headers
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE section_header IS NOT NULL AND section_header != ''")
 if cur.fetchone()[0] > 100:
 requirements['Section headers'] = True
 
 # Check page references
 cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE page_number IS NOT NULL")
 if cur.fetchone()[0] > 100:
 requirements['Page references'] = True
 
 print("Requirements checklist:")
 for req, status in requirements.items():
 status_icon = "" if status else ""
 print(f" {status_icon} {req}")
 
 # Overall readiness
 ready_count = sum(requirements.values())
 total_count = len(requirements)
 readiness_pct = (ready_count / total_count) * 100
 
 print(f"\nOverall readiness: {ready_count}/{total_count} ({readiness_pct:.1f}%)")
 
 if readiness_pct >= 80:
 print(" READY: Can implement accordion with current data!")
 elif readiness_pct >= 60:
 print(" MOSTLY READY: Minor gaps to address")
 else:
 print(" NEEDS WORK: Significant data gaps")
 
 conn.close()
 
 return requirements

def main():
 """Run comprehensive clause pipeline analysis"""
 print("NSW PLANNING COMPLIANCE ENGINE")
 print("Clause Text Pipeline Analysis for Referenced Legislation Accordion\n")
 
 try:
 analyze_database_schema()
 analyze_clause_text_content()
 analyze_current_api_response()
 analyze_linking_structure()
 requirements = assess_accordion_readiness()
 
 # Generate recommendations
 print("\n=== RECOMMENDATIONS ===\n")
 
 if not requirements['Full clause text']:
 print(" CRITICAL: Need to ensure full clause text is extracted and stored")
 
 if not requirements['Provision-to-control linking']:
 print(" CRITICAL: Need to link setback controls to specific regulatory provisions")
 
 if requirements['Full clause text'] and requirements['Provision-to-control linking']:
 print(" Ready to implement basic accordion feature!")
 print(" - Modify setback calculator to return provision IDs")
 print(" - Create API endpoint to fetch clause details by provision ID")
 print(" - Add accordion component to frontend")
 
 except Exception as e:
 print(f"Analysis error: {e}")

if __name__ == "__main__":
 main()