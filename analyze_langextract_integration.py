#!/usr/bin/env python3
"""
Analyze LangExtract Integration with AutoSchemaKG
================================================

Examines how LangExtract structure preservation and AutoSchemaKG integration 
are currently stored in the database and designs preservation strategy.
"""

import sqlite3
from collections import defaultdict, Counter

def analyze_langextract_structure():
 """Analyze LangExtract structure indicators in the database"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 print("=" * 80)
 print("LANGEXTRACT STRUCTURE ANALYSIS")
 print("=" * 80)
 
 # 1. Text level analysis
 print("\n1. TEXT LEVEL HIERARCHY:")
 levels = cur.execute('''
 SELECT text_level, COUNT(*) 
 FROM regulatory_refs 
 WHERE text_level IS NOT NULL 
 GROUP BY text_level 
 ORDER BY text_level
 ''').fetchall()
 
 if levels:
 for level, count in levels:
 print(f" Level {level}: {count:,} entries")
 
 # Show distribution by text level
 total_with_levels = sum(count for _, count in levels)
 total_entries = cur.execute("SELECT COUNT(*) FROM regulatory_refs").fetchone()[0]
 print(f" Total with text_level: {total_with_levels:,}/{total_entries:,} ({total_with_levels/total_entries*100:.1f}%)")
 else:
 print(" No text_level data found")
 
 # 2. Page number + section header correlation (LangExtract signature)
 print("\n2. LANGEXTRACT SIGNATURE ANALYSIS:")
 
 langextract_indicators = cur.execute('''
 SELECT 
 COUNT(*) as total,
 COUNT(CASE WHEN page_number IS NOT NULL THEN 1 END) as with_pages,
 COUNT(CASE WHEN section_header IS NOT NULL THEN 1 END) as with_sections,
 COUNT(CASE WHEN page_number IS NOT NULL AND section_header IS NOT NULL THEN 1 END) as with_both,
 COUNT(CASE WHEN text_level IS NOT NULL THEN 1 END) as with_levels
 FROM regulatory_refs
 ''').fetchone()
 
 total, with_pages, with_sections, with_both, with_levels = langextract_indicators
 
 print(f" Total entries: {total:,}")
 print(f" With page numbers: {with_pages:,} ({with_pages/total*100:.1f}%)")
 print(f" With section headers: {with_sections:,} ({with_sections/total*100:.1f}%)")
 print(f" With BOTH page & section: {with_both:,} ({with_both/total*100:.1f}%)")
 print(f" With text levels: {with_levels:,} ({with_levels/total*100:.1f}%)")
 
 # 3. Quality of LangExtract entries
 print("\n3. LANGEXTRACT QUALITY INDICATORS:")
 
 # Entries with rich structure (likely from LangExtract)
 high_quality = cur.execute('''
 SELECT COUNT(*) 
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL 
 AND section_header IS NOT NULL 
 AND LENGTH(ref_context) > 50
 ''').fetchone()[0]
 
 print(f" High-quality entries (page + section + content): {high_quality:,}")
 
 # Sample high-quality entries
 samples = cur.execute('''
 SELECT ref_type, ref_number, page_number, section_header, ref_context
 FROM regulatory_refs 
 WHERE page_number IS NOT NULL 
 AND page_number > 0
 AND section_header IS NOT NULL 
 AND LENGTH(ref_context) > 100
 ORDER BY page_number, LENGTH(ref_context) DESC
 LIMIT 5
 ''').fetchall()
 
 print(f"\n Sample high-quality LangExtract entries:")
 for i, (ref_type, ref_number, page_num, section, context) in enumerate(samples, 1):
 print(f" {i}. {ref_type} | Page {page_num}")
 print(f" Reference: {ref_number}")
 print(f" Section: {section[:60]}...")
 print(f" Context: {context[:100]}...")
 print()
 
 conn.close()
 return {
 'total_entries': total,
 'with_pages': with_pages,
 'with_sections': with_sections, 
 'with_both': with_both,
 'with_levels': with_levels,
 'high_quality': high_quality
 }

def analyze_autoschema_langextract_integration():
 """Analyze how AutoSchemaKG integrated with LangExtract"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 print("=" * 80)
 print("AUTOSCHEMA-LANGEXTRACT INTEGRATION ANALYSIS")
 print("=" * 80)
 
 # 1. AutoSchema entries with LangExtract metadata
 print("\n1. AUTOSCHEMA ENTRIES WITH LANGEXTRACT METADATA:")
 
 autoschema_with_pages = cur.execute('''
 SELECT 
 ref_type,
 COUNT(*) as total,
 COUNT(CASE WHEN page_number IS NOT NULL THEN 1 END) as with_pages,
 COUNT(CASE WHEN section_header IS NOT NULL THEN 1 END) as with_sections
 FROM regulatory_refs 
 WHERE ref_type LIKE 'autoschema_%'
 GROUP BY ref_type
 ORDER BY total DESC
 ''').fetchall()
 
 for ref_type, total, with_pages, with_sections in autoschema_with_pages:
 element_type = ref_type.replace('autoschema_', '')
 page_pct = with_pages/total*100 if total > 0 else 0
 section_pct = with_sections/total*100 if total > 0 else 0
 print(f" {element_type}: {total:,} entries")
 print(f" With pages: {with_pages:,} ({page_pct:.1f}%)")
 print(f" With sections: {with_sections:,} ({section_pct:.1f}%)")
 
 # 2. Visual-clause relationships with page context
 print("\n2. VISUAL-CLAUSE RELATIONSHIPS WITH PAGE CONTEXT:")
 
 visual_clause_links = cur.execute('''
 SELECT page_number, section_header, ref_number, ref_context
 FROM regulatory_refs 
 WHERE ref_type = 'autoschema_relationship_illustrates_clause'
 AND page_number IS NOT NULL
 ORDER BY page_number
 LIMIT 5
 ''').fetchall()
 
 if visual_clause_links:
 print(f" Found {len(visual_clause_links)} visual-clause links with page context:")
 for page_num, section, ref_num, context in visual_clause_links:
 print(f" Page {page_num}: {ref_num}")
 print(f" Section: {section[:50] if section else 'No section'}...")
 print(f" Context: {context[:80] if context else 'No context'}...")
 print()
 else:
 print(" No visual-clause links with page context found")
 
 # 3. Cross-reference analysis: entities mentioned in formal provisions
 print("\n3. CROSS-REFERENCE INTEGRATION:")
 
 # Find formal provisions that mention visual elements
 formal_with_visual_refs = cur.execute('''
 SELECT COUNT(*) 
 FROM regulatory_refs 
 WHERE ref_type LIKE 'formal_%'
 AND (ref_context LIKE '%image%' OR ref_context LIKE '%figure%' 
 OR ref_context LIKE '%diagram%' OR ref_context LIKE '%table%')
 ''').fetchone()[0]
 
 print(f" Formal provisions mentioning visual elements: {formal_with_visual_refs:,}")
 
 # Find entities that have both AutoSchema and LangExtract data
 entity_integration = cur.execute('''
 SELECT 
 COUNT(DISTINCT ref_number) as unique_entities
 FROM regulatory_refs r1
 WHERE ref_type LIKE 'entity_%'
 AND EXISTS (
 SELECT 1 FROM regulatory_refs r2 
 WHERE r2.ref_number = r1.ref_number 
 AND r2.page_number IS NOT NULL
 )
 ''').fetchone()[0]
 
 print(f" Entities with page context: {entity_integration:,}")
 
 conn.close()
 return {
 'autoschema_types': len(autoschema_with_pages),
 'visual_clause_links': len(visual_clause_links) if visual_clause_links else 0,
 'formal_with_visual': formal_with_visual_refs,
 'entities_with_pages': entity_integration
 }

def identify_langextract_autoschema_workflow():
 """Identify the workflow integration between LangExtract and AutoSchemaKG"""
 
 print("=" * 80)
 print("LANGEXTRACT-AUTOSCHEMA WORKFLOW IDENTIFICATION")
 print("=" * 80)
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # 1. Document processing workflow analysis
 print("\n1. DOCUMENT PROCESSING WORKFLOW:")
 
 # Check for documents with both structured and visual data
 doc_analysis = cur.execute('''
 SELECT 
 document_id,
 COUNT(*) as total_refs,
 COUNT(CASE WHEN ref_type LIKE 'formal_%' THEN 1 END) as formal_refs,
 COUNT(CASE WHEN ref_type LIKE 'autoschema_%' THEN 1 END) as visual_refs,
 COUNT(CASE WHEN page_number IS NOT NULL THEN 1 END) as page_refs
 FROM regulatory_refs 
 GROUP BY document_id
 HAVING total_refs > 100 -- Focus on substantial documents
 ORDER BY total_refs DESC
 LIMIT 5
 ''').fetchall()
 
 print(f" Analysis of top 5 most processed documents:")
 for doc_id, total, formal, visual, pages in doc_analysis:
 doc_name = doc_id[:50] + "..." if len(doc_id) > 50 else doc_id
 formal_pct = formal/total*100 if total > 0 else 0
 visual_pct = visual/total*100 if total > 0 else 0
 page_pct = pages/total*100 if total > 0 else 0
 
 print(f" {doc_name}")
 print(f" Total: {total:,} | Formal: {formal:,} ({formal_pct:.1f}%) | Visual: {visual:,} ({visual_pct:.1f}%) | Pages: {pages:,} ({page_pct:.1f}%)")
 
 # 2. Workflow sequence indicators
 print("\n2. PROCESSING SEQUENCE INDICATORS:")
 
 # Check timestamps to understand processing order
 time_analysis = cur.execute('''
 SELECT 
 ref_type,
 MIN(id) as first_id,
 MAX(id) as last_id,
 COUNT(*) as count
 FROM regulatory_refs 
 WHERE ref_type IN (
 SELECT ref_type FROM regulatory_refs 
 WHERE ref_type LIKE 'formal_%' OR ref_type LIKE 'autoschema_%' 
 GROUP BY ref_type 
 HAVING COUNT(*) > 50
 )
 GROUP BY ref_type
 ORDER BY first_id
 LIMIT 10
 ''').fetchall()
 
 print(f" Processing sequence (by first appearance in database):")
 for ref_type, first_id, last_id, count in time_analysis:
 print(f" {ref_type}: IDs {first_id}-{last_id} ({count:,} entries)")
 
 conn.close()

def design_preservation_strategy():
 """Design strategy to preserve LangExtract-AutoSchemaKG integration"""
 
 print("=" * 80)
 print("LANGEXTRACT-AUTOSCHEMA PRESERVATION STRATEGY")
 print("=" * 80)
 
 print("\nPRESERVATION REQUIREMENTS:")
 
 preservation_needs = {
 "Document Structure Hierarchy": {
 "current": "text_level field indicates document hierarchy",
 "preserve": "Create document_structure table with full TOC hierarchy",
 "benefit": "Maintains document navigation and context"
 },
 
 "Page-Perfect Citations": {
 "current": "2,518 entries have page numbers (11.4%)",
 "preserve": "Ensure every migrated entry retains page_number field",
 "benefit": "Council-ready citations for all regulatory content"
 },
 
 "Section Context": {
 "current": "2,518 entries have section headers",
 "preserve": "Create section_metadata table with full section context",
 "benefit": "Rich contextual information for regulatory provisions"
 },
 
 "Visual-Clause Integration": {
 "current": "351 autoschema_relationship_illustrates_clause entries",
 "preserve": "Direct foreign key relationships between visual and textual content",
 "benefit": "Maintain multimodal regulatory intelligence"
 },
 
 "Entity-Page Mapping": {
 "current": "184 entities have page references",
 "preserve": "All entity entries include page_number and section_header",
 "benefit": "Traceable entities with precise document locations"
 }
 }
 
 for requirement, details in preservation_needs.items():
 print(f"\n {requirement}:")
 print(f" Current: {details['current']}")
 print(f" Preserve: {details['preserve']}")
 print(f" Benefit: {details['benefit']}")
 
 print("\nENHANCED MIGRATION SCHEMA:")
 
 enhanced_tables = {
 "document_structure": '''
 CREATE TABLE document_structure (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 document_id TEXT NOT NULL,
 section_number TEXT,
 section_title TEXT,
 section_level INTEGER, -- From LangExtract text_level
 parent_section_id INTEGER,
 page_number INTEGER,
 section_order INTEGER,
 FOREIGN KEY (document_id) REFERENCES documents (id),
 FOREIGN KEY (parent_section_id) REFERENCES document_structure (id)
 )
 ''',
 
 "page_metadata": '''
 CREATE TABLE page_metadata (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 document_id TEXT NOT NULL,
 page_number INTEGER NOT NULL,
 page_content_summary TEXT,
 section_headers TEXT, -- JSON array of sections on this page
 visual_elements_count INTEGER DEFAULT 0,
 regulatory_provisions_count INTEGER DEFAULT 0,
 extraction_quality_score REAL,
 FOREIGN KEY (document_id) REFERENCES documents (id)
 )
 ''',
 
 "multimodal_integration": '''
 CREATE TABLE multimodal_integration (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 text_provision_id INTEGER,
 visual_element_id INTEGER,
 relationship_type TEXT, -- 'illustrates', 'supports', 'defines'
 confidence_score REAL DEFAULT 1.0,
 page_number INTEGER,
 integration_method TEXT, -- 'autoschema', 'langextract', 'manual'
 FOREIGN KEY (text_provision_id) REFERENCES regulatory_provisions (id),
 FOREIGN KEY (visual_element_id) REFERENCES kg_visual_elements (id)
 )
 '''
 }
 
 for table_name, schema in enhanced_tables.items():
 print(f"\n {table_name.upper()}:")
 # Extract purpose from CREATE statement
 lines = schema.strip().split('\n')
 columns = [line.strip() for line in lines if '(' in line and 'CREATE' not in line and 'FOREIGN' not in line][:4]
 print(f" Key columns: {', '.join(col.split()[0] for col in columns if col)}")
 
 print("\nMIGRATION ENHANCEMENTS:")
 enhancements = [
 "Add document_structure extraction from text_level data",
 "Create page_metadata from LangExtract page/section mappings", 
 "Build multimodal_integration from autoschema_relationship entries",
 "Preserve all LangExtract quality indicators (page + section + content)",
 "Maintain processing provenance for debugging and validation"
 ]
 
 for i, enhancement in enumerate(enhancements, 1):
 print(f" {i}. {enhancement}")

def main():
 """Main analysis function"""
 
 # Analyze current LangExtract structure
 langextract_stats = analyze_langextract_structure()
 
 # Analyze AutoSchemaKG integration
 integration_stats = analyze_autoschema_langextract_integration()
 
 # Identify workflow
 identify_langextract_autoschema_workflow()
 
 # Design preservation strategy
 design_preservation_strategy()
 
 print("\n" + "=" * 80)
 print("SUMMARY: LANGEXTRACT-AUTOSCHEMA INTEGRATION")
 print("=" * 80)
 
 print(f"\nCURRENT STATE:")
 print(f" - {langextract_stats['with_both']:,} entries with LangExtract structure (page + section)")
 print(f" - {integration_stats['visual_clause_links']:,} visual-clause relationships")
 print(f" - {integration_stats['entities_with_pages']:,} entities with page context")
 print(f" - {langextract_stats['high_quality']:,} high-quality structured entries")
 
 print(f"\nPRESERVATION PRIORITY:")
 print(f" 1. HIGH: Preserve page numbers and section headers for all 2,518 entries")
 print(f" 2. HIGH: Maintain visual-clause relationships (351 links)")
 print(f" 3. MEDIUM: Document structure hierarchy from text_level")
 print(f" 4. MEDIUM: Multimodal integration metadata")
 
 print(f"\nSOLUTION:")
 print(f" - Enhanced migration schema with LangExtract preservation")
 print(f" - Direct integration between textual and visual elements")
 print(f" - Complete processing provenance tracking")
 print(f" - No loss of citation quality or multimodal relationships")

if __name__ == "__main__":
 main()