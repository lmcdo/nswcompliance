#!/usr/bin/env python3
"""
Analyze the database to determine the INTENDED schema based on:
1. What data types are actually extracted
2. How the UI expects to query the data 
3. The app's compliance checking purpose
"""

import sqlite3
import json
from collections import defaultdict, Counter

def analyze_extracted_data():
 """Analyze what data types are actually in the database"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 print("=" * 80)
 print("ANALYZING EXTRACTED DATA TO DETERMINE INTENDED SCHEMA")
 print("=" * 80)
 
 # Get all ref_types and their patterns
 print("\nANALYZING REF_TYPES:")
 ref_types = cur.execute("""
 SELECT ref_type, COUNT(*) as count
 FROM regulatory_refs 
 GROUP BY ref_type 
 ORDER BY count DESC
 """).fetchall()
 
 # Categorize by prefixes to understand intended structure
 categories = defaultdict(list)
 for ref_type, count in ref_types:
 if '_' in ref_type:
 prefix = ref_type.split('_')[0]
 categories[prefix].append((ref_type, count))
 else:
 categories['direct'].append((ref_type, count))
 
 print(f"\nINTENDED DATA CATEGORIES (by prefix):")
 total_entries = 0
 
 for category, items in sorted(categories.items(), key=lambda x: sum(item[1] for item in x[1]), reverse=True):
 category_total = sum(item[1] for item in items)
 total_entries += category_total
 print(f"\n {category.upper()}: {category_total:,} entries")
 
 # Show top items in each category
 for ref_type, count in sorted(items, key=lambda x: x[1], reverse=True)[:5]:
 percentage = count/category_total*100
 print(f" {ref_type}: {count:,} ({percentage:.1f}%)")
 
 if len(items) > 5:
 print(f" ... and {len(items)-5} more types")
 
 print(f"\nTotal entries analyzed: {total_entries:,}")
 
 # Analyze specific high-value data
 print(f"\nHIGH-VALUE COMPLIANCE DATA:")
 
 high_value_patterns = [
 ('setback', 'building setbacks|setback'),
 ('height', 'building height|height'),
 ('zoning', 'zone|zoning'),
 ('heritage', 'heritage'),
 ('development_standards', 'development.*standard'),
 ('assessment', 'assessment'),
 ('clause', 'clause|section')
 ]
 
 for pattern_name, pattern in high_value_patterns:
 count = cur.execute(f"""
 SELECT COUNT(*) FROM regulatory_refs 
 WHERE ref_context LIKE '%{pattern.split('|')[0]}%' 
 OR ref_type LIKE '%{pattern.split('|')[0]}%'
 OR ref_number LIKE '%{pattern.split('|')[0]}%'
 """).fetchone()[0]
 
 if count > 0:
 print(f" {pattern_name}: {count:,} references")
 
 # Sample actual content to understand data quality
 print(f"\nSAMPLE COMPLIANCE CONTENT:")
 
 samples = cur.execute("""
 SELECT ref_type, ref_number, ref_context, page_number, section_header
 FROM regulatory_refs 
 WHERE (ref_type LIKE '%setback%' OR ref_context LIKE '%setback%')
 OR (ref_type LIKE '%height%' OR ref_context LIKE '%height%')
 OR (ref_type LIKE '%zone%' OR ref_context LIKE '%zone%')
 AND ref_context IS NOT NULL 
 AND LENGTH(ref_context) > 50
 ORDER BY RANDOM()
 LIMIT 5
 """).fetchall()
 
 for i, (ref_type, ref_number, ref_context, page_number, section_header) in enumerate(samples, 1):
 print(f"\n Sample {i}:")
 print(f" Type: {ref_type}")
 print(f" Number: {ref_number}")
 print(f" Page: {page_number}")
 print(f" Section: {section_header}")
 print(f" Content: {ref_context[:100]}...")
 
 conn.close()
 return categories

def analyze_ui_expectations():
 """Analyze what the UI expects to query"""
 
 print(f"\n" + "=" * 80)
 print("ANALYZING UI QUERY EXPECTATIONS") 
 print("=" * 80)
 
 # Check what the frontend and services are trying to query
 frontend_queries = []
 
 # Check frontend JavaScript
 try:
 with open('frontend/index.html', 'r', encoding='utf-8') as f:
 frontend_content = f.read()
 
 # Look for API calls and data expectations
 if 'setback' in frontend_content.lower():
 frontend_queries.append("Setback calculations")
 if 'height' in frontend_content.lower():
 frontend_queries.append("Height limits") 
 if 'zone' in frontend_content.lower():
 frontend_queries.append("Zoning information")
 if 'heritage' in frontend_content.lower():
 frontend_queries.append("Heritage controls")
 
 print(f"\nFRONTEND EXPECTS:")
 for query in frontend_queries:
 print(f" - {query}")
 
 except Exception as e:
 print(f"Could not analyze frontend: {e}")
 
 # Check what services are querying
 service_files = [
 'services/authoritative_setback_calculator.py',
 'services/universal_regulatory_engine.py',
 'api_server.py'
 ]
 
 service_expectations = []
 
 for service_file in service_files:
 try:
 with open(service_file, 'r', encoding='utf-8') as f:
 content = f.read()
 
 # Look for SQL queries and data expectations
 if 'SELECT' in content and 'regulatory_refs' in content:
 service_expectations.append(f"{service_file}: Queries regulatory_refs table")
 if 'entities' in content and 'relationships' in content:
 service_expectations.append(f"{service_file}: Expects entities/relationships tables")
 if 'setback' in content.lower():
 service_expectations.append(f"{service_file}: Needs setback data")
 if 'page_number' in content:
 service_expectations.append(f"{service_file}: Needs page number citations")
 
 except Exception as e:
 continue
 
 print(f"\nSERVICES EXPECT:")
 for expectation in service_expectations:
 print(f" - {expectation}")
 
 return frontend_queries, service_expectations

def analyze_app_purpose():
 """Analyze the app's intended purpose from documentation"""
 
 print(f"\n" + "=" * 80)
 print("ANALYZING APPLICATION PURPOSE")
 print("=" * 80)
 
 # Read key documentation files
 doc_files = [
 'README.md',
 'PRP-ULTIMATE_MULTIMODAL_EXTRACTION.md',
 'PLANNING.md'
 ]
 
 purposes = []
 
 for doc_file in doc_files:
 try:
 with open(doc_file, 'r', encoding='utf-8') as f:
 content = f.read().lower()
 
 # Extract purpose indicators
 if 'compliance' in content:
 purposes.append("Compliance checking")
 if 'setback' in content:
 purposes.append("Setback calculations") 
 if 'planning' in content and 'rules' in content:
 purposes.append("Planning rule queries")
 if 'property' in content and 'development' in content:
 purposes.append("Property development guidance")
 if 'council' in content:
 purposes.append("Council-ready assessments")
 
 except Exception as e:
 continue
 
 print(f"\nAPPLICATION PURPOSE:")
 for purpose in set(purposes):
 print(f" - {purpose}")
 
 return purposes

def recommend_ideal_schema(categories, frontend_queries, service_expectations, purposes):
 """Recommend the ideal database schema based on analysis"""
 
 print(f"\n" + "=" * 80)
 print("RECOMMENDED IDEAL SCHEMA")
 print("=" * 80)
 
 print(f"\nBASED ON ANALYSIS:")
 print(f" - {sum(len(items) for items in categories.values())} different data types")
 print(f" - Frontend needs: {len(frontend_queries)} query types")
 print(f" - Services need: {len(service_expectations)} capabilities")
 print(f" - App purposes: {len(purposes)} main functions")
 
 print(f"\nRECOMMENDED TABLES:")
 
 # Core compliance tables
 tables = {
 "documents": {
 "purpose": "Store PDF documents and metadata",
 "columns": ["id", "pdf_name", "document_type", "document_area", "pdf_path", "char_count", "word_count", "extraction_timestamp", "full_text"],
 "current_status": "EXISTS - Keep as is"
 },
 
 "regulatory_provisions": {
 "purpose": "Core regulatory requirements (clauses, standards, controls)",
 "columns": ["id", "document_id", "provision_type", "clause_number", "provision_text", "page_number", "section_header", "applies_to", "measurements"],
 "current_status": "MISSING - Should contain formal_* and development_standards data",
 "data_source": "Currently scattered across regulatory_refs with formal_* prefixes"
 },
 
 "development_controls": {
 "purpose": "Specific development controls (setbacks, heights, FSR)",
 "columns": ["id", "provision_id", "control_type", "control_value", "measurement_unit", "applies_to_zone", "conditions"],
 "current_status": "MISSING - Critical for compliance calculations",
 "data_source": "Currently mixed in regulatory_refs"
 },
 
 "zoning_information": {
 "purpose": "Land use zones and permitted development",
 "columns": ["id", "zone_code", "zone_name", "permitted_uses", "prohibited_uses", "development_standards", "document_id"],
 "current_status": "MISSING - Needed for property queries",
 "data_source": "Currently in entity_zone entries"
 },
 
 "contextual_guidance": {
 "purpose": "Non-binding guidance, character descriptions, design intent",
 "columns": ["id", "document_id", "guidance_type", "guidance_text", "page_number", "relates_to_provision"],
 "current_status": "MISSING - Should contain context_* data",
 "data_source": "Currently context_* entries in regulatory_refs"
 },
 
 "visual_elements": {
 "purpose": "Images, diagrams, tables with regulatory context",
 "columns": ["id", "document_id", "element_type", "file_path", "page_number", "clause_context", "description"],
 "current_status": "MISSING - Should contain autoschema_* data",
 "data_source": "Currently autoschema_* entries in regulatory_refs"
 },
 
 "cross_references": {
 "purpose": "Relationships between provisions, SEPPs, LEPs, DCPs",
 "columns": ["id", "from_provision", "to_provision", "relationship_type", "reference_text"],
 "current_status": "MISSING - No proper relationship tracking",
 "data_source": "Should be extracted from formal_* relationships"
 },
 
 "page_citations": {
 "purpose": "Precise page and section citations for all content",
 "columns": ["id", "content_id", "content_type", "page_number", "section_header", "text_before", "text_after"],
 "current_status": "PARTIAL - Only 11.4% have page numbers",
 "data_source": "Currently page_number, section_header in regulatory_refs"
 }
 }
 
 for table_name, info in tables.items():
 print(f"\n {table_name.upper()}:")
 print(f" Purpose: {info['purpose']}")
 print(f" Status: {info['current_status']}")
 if 'data_source' in info:
 print(f" Data source: {info['data_source']}")
 print(f" Columns: {', '.join(info['columns'])}")
 
 # Migration priority
 print(f"\nMIGRATION PRIORITY:")
 priority_order = [
 ("HIGH", "regulatory_provisions", "Core compliance logic depends on this"),
 ("HIGH", "development_controls", "Setback/height calculations need this"), 
 ("HIGH", "page_citations", "Citations required for council compliance"),
 ("MEDIUM", "zoning_information", "Property queries need zone data"),
 ("MEDIUM", "cross_references", "Improves regulatory intelligence"),
 ("LOW", "contextual_guidance", "Nice-to-have for comprehensive responses"),
 ("LOW", "visual_elements", "Enhances but not critical for core function")
 ]
 
 for priority, table, reason in priority_order:
 print(f" {priority:6} - {table:20} ({reason})")
 
 return tables

def main():
 """Main analysis function"""
 
 categories = analyze_extracted_data()
 frontend_queries, service_expectations = analyze_ui_expectations() 
 purposes = analyze_app_purpose()
 
 ideal_schema = recommend_ideal_schema(categories, frontend_queries, service_expectations, purposes)
 
 print(f"\n" + "=" * 80)
 print("SUMMARY: WHAT THE SCHEMA SHOULD BE")
 print("=" * 80)
 
 print(f"\nCURRENT PROBLEM:")
 print(f" - One giant regulatory_refs table with 22,092 mixed entries")
 print(f" - {len(categories)} different data types crammed together")
 print(f" - UI expects normalized schema but gets flat data")
 print(f" - Only 11.4% of entries have page numbers")
 
 print(f"\nSOLUTION:")
 print(f" - Create {len(ideal_schema)} properly normalized tables")
 print(f" - Migrate data by ref_type prefix patterns")
 print(f" - Add missing page citations to all entries")
 print(f" - Enable proper compliance calculations")
 
 print(f"\nNEXT STEPS:")
 print(f" 1. Create migration script to split regulatory_refs")
 print(f" 2. Build proper normalized schema")
 print(f" 3. Update UI services to query new tables")
 print(f" 4. Add missing page number citations")
 print(f" 5. Test compliance calculations work correctly")

if __name__ == "__main__":
 main()