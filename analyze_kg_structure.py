#!/usr/bin/env python3
"""
Analyze Knowledge Graph Structure in Current Database
====================================================

Examines how AutoSchemaKG entities, relationships, and triples are stored
and determines proper preservation strategy.
"""

import sqlite3
import json
from collections import defaultdict

def analyze_kg_structure():
 """Analyze the knowledge graph structure currently in the database"""
 
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 print("=" * 80)
 print("KNOWLEDGE GRAPH STRUCTURE ANALYSIS")
 print("=" * 80)
 
 # 1. Examine relationship types and patterns
 print("\n1. RELATIONSHIP PATTERNS:")
 relationships = cur.execute("""
 SELECT ref_type, ref_number, ref_context
 FROM regulatory_refs 
 WHERE ref_type LIKE 'relationship_%'
 ORDER BY ref_type, ref_number
 LIMIT 20
 """).fetchall()
 
 for rel_type, ref_number, context in relationships:
 relationship_name = rel_type.replace('relationship_', '')
 print(f" {relationship_name}: {ref_number} -> {context[:80]}...")
 
 # 2. Examine entity types
 print(f"\n2. ENTITY TYPES:")
 entities = cur.execute("""
 SELECT ref_type, ref_number, ref_context
 FROM regulatory_refs 
 WHERE ref_type LIKE 'entity_%'
 ORDER BY ref_type, ref_number
 LIMIT 20
 """).fetchall()
 
 for ent_type, ref_number, context in entities:
 entity_name = ent_type.replace('entity_', '')
 print(f" {entity_name}: {ref_number} -> {context[:80]}...")
 
 # 3. Examine AutoSchema data
 print(f"\n3. AUTOSCHEMA ELEMENTS:")
 autoschema = cur.execute("""
 SELECT ref_type, ref_number, ref_context, page_number
 FROM regulatory_refs 
 WHERE ref_type LIKE 'autoschema_%'
 ORDER BY ref_type, ref_number
 LIMIT 10
 """).fetchall()
 
 for auto_type, ref_number, context, page in autoschema:
 element_type = auto_type.replace('autoschema_', '')
 page_info = f" [Page {page}]" if page else ""
 print(f" {element_type}: {ref_number} -> {context[:60]}...{page_info}")
 
 # 4. Check for triple patterns (subject-predicate-object)
 print(f"\n4. POTENTIAL TRIPLE STRUCTURES:")
 
 # Look for patterns that suggest triples
 triple_patterns = cur.execute("""
 SELECT ref_type, ref_number, ref_context
 FROM regulatory_refs 
 WHERE ref_type LIKE 'relationship_%'
 AND ref_number LIKE '%->%'
 LIMIT 10
 """).fetchall()
 
 if triple_patterns:
 print(" Found arrow-based triples:")
 for rel_type, ref_number, context in triple_patterns:
 parts = ref_number.split(' -> ')
 if len(parts) >= 2:
 subject = parts[0]
 obj = parts[1] if len(parts) > 1 else "?"
 predicate = rel_type.replace('relationship_', '')
 print(f" TRIPLE: [{subject}] --{predicate}--> [{obj}]")
 print(f" Context: {context[:100]}...")
 else:
 print(" No clear triple patterns with arrows found")
 
 # 5. Check for structured entity references
 print(f"\n5. STRUCTURED REFERENCES:")
 
 # Count cross-references between entities
 cross_refs = defaultdict(int)
 
 # Look for entity names mentioned in relationship contexts
 entity_data = cur.execute("SELECT DISTINCT ref_number FROM regulatory_refs WHERE ref_type LIKE 'entity_%'").fetchall()
 entity_names = [row[0] for row in entity_data]
 
 print(f" Found {len(entity_names)} distinct entity references")
 
 # Sample some complex relationships
 complex_rels = cur.execute("""
 SELECT ref_type, ref_number, ref_context
 FROM regulatory_refs 
 WHERE ref_type LIKE 'relationship_%'
 AND LENGTH(ref_context) > 200
 ORDER BY LENGTH(ref_context) DESC
 LIMIT 5
 """).fetchall()
 
 print(f"\n6. COMPLEX RELATIONSHIPS (likely containing multiple entities):")
 for i, (rel_type, ref_number, context) in enumerate(complex_rels, 1):
 predicate = rel_type.replace('relationship_', '')
 print(f" {i}. {predicate}: {ref_number}")
 print(f" Context: {context[:150]}...")
 
 # Look for entity mentions in context
 mentioned_entities = []
 for entity_name in entity_names[:20]: # Check subset
 if entity_name.lower() in context.lower():
 mentioned_entities.append(entity_name)
 
 if mentioned_entities:
 print(f" Mentions: {', '.join(mentioned_entities[:3])}...")
 
 # 7. Statistics
 print(f"\n7. KNOWLEDGE GRAPH STATISTICS:")
 
 stats = {}
 for prefix in ['relationship_', 'entity_', 'autoschema_']:
 count = cur.execute(f"SELECT COUNT(*) FROM regulatory_refs WHERE ref_type LIKE '{prefix}%'").fetchone()[0]
 stats[prefix.rstrip('_')] = count
 print(f" {prefix.rstrip('_')}: {count:,} entries")
 
 # Check relationships with page numbers
 rel_with_pages = cur.execute("""
 SELECT COUNT(*) FROM regulatory_refs 
 WHERE ref_type LIKE 'relationship_%' AND page_number IS NOT NULL
 """).fetchone()[0]
 
 ent_with_pages = cur.execute("""
 SELECT COUNT(*) FROM regulatory_refs 
 WHERE ref_type LIKE 'entity_%' AND page_number IS NOT NULL
 """).fetchone()[0]
 
 print(f" Relationships with page numbers: {rel_with_pages:,}")
 print(f" Entities with page numbers: {ent_with_pages:,}")
 
 conn.close()
 return stats

def recommend_kg_preservation():
 """Recommend how to properly preserve knowledge graph structure"""
 
 print(f"\n" + "=" * 80)
 print("KNOWLEDGE GRAPH PRESERVATION STRATEGY")
 print("=" * 80)
 
 print(f"\nCURRENT PROBLEM:")
 print(f" - AutoSchemaKG triples are flattened into regulatory_refs")
 print(f" - Entity-relationship structure is lost")
 print(f" - No proper subject-predicate-object preservation")
 print(f" - Page numbers only partially preserved")
 
 print(f"\nPROPER SOLUTION:")
 print(f" Create separate knowledge graph tables alongside content tables:")
 
 kg_schema = {
 "kg_entities": {
 "purpose": "Store all extracted entities (zones, controls, heritage items, etc.)",
 "columns": ["id", "entity_type", "entity_name", "entity_description", "document_id", "page_number", "section_header"],
 "data_source": "entity_* entries from regulatory_refs"
 },
 
 "kg_relationships": {
 "purpose": "Store relationships between entities (triples: subject-predicate-object)",
 "columns": ["id", "subject_entity_id", "predicate", "object_entity_id", "relationship_text", "document_id", "page_number"],
 "data_source": "relationship_* entries from regulatory_refs"
 },
 
 "kg_visual_links": {
 "purpose": "Link visual elements (images/tables) to specific clauses",
 "columns": ["id", "visual_element_id", "clause_reference", "illustration_type", "page_number"],
 "data_source": "autoschema_relationship_illustrates_clause entries"
 },
 
 "kg_entity_mentions": {
 "purpose": "Track where entities are mentioned in regulatory text",
 "columns": ["id", "entity_id", "provision_id", "mention_context", "page_number"],
 "data_source": "Cross-reference between entities and provisions"
 }
 }
 
 for table, info in kg_schema.items():
 print(f"\n {table.upper()}:")
 print(f" Purpose: {info['purpose']}")
 print(f" Data source: {info['data_source']}")
 print(f" Columns: {', '.join(info['columns'])}")
 
 print(f"\nMIGRATION STRATEGY:")
 print(f" 1. Parse relationship entries to extract subject-predicate-object triples")
 print(f" 2. Create entity lookup table from entity_* entries") 
 print(f" 3. Link relationships to entity IDs instead of text names")
 print(f" 4. Preserve all AutoSchema visual-clause mappings")
 print(f" 5. Maintain page number citations throughout")
 
 print(f"\nBENEFITS:")
 print(f" - Proper knowledge graph queries (find all entities of type X)")
 print(f" - Relationship traversal (what does entity A connect to?)")
 print(f" - Visual element integration (show diagrams for clause Y)")
 print(f" - Full citation tracking (every KG element has page numbers)")

def main():
 """Main analysis function"""
 stats = analyze_kg_structure()
 recommend_kg_preservation()
 
 print(f"\n" + "=" * 80)
 print("SUMMARY")
 print("=" * 80)
 print(f" - {stats.get('relationship', 0):,} relationships need proper triple storage")
 print(f" - {stats.get('entity', 0):,} entities need normalized entity table")
 print(f" - {stats.get('autoschema', 0):,} visual elements need visual-clause links")
 print(f" - Current migration plan will DESTROY this knowledge graph structure!")
 print(f" - Need to add KG-specific tables to migration script")

if __name__ == "__main__":
 main()