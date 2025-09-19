# PRP-K7: Database Architecture Analysis - Existing vs Future Zone Import

## Current Database Architecture Analysis

### Core Entity-Relationship Structure

The existing database has a sophisticated multi-layered architecture designed to preserve AutoSchemaKG entities, RAG-Anything visual elements, and LangExtract provisions:

```
CURRENT ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│ kg_entities (10,000+ entities)                                 │
│ ├─ entity_type, entity_name, entity_description                │
│ ├─ document_id, page_number, section_header                    │
│ └─ original_ref_type, original_ref_id (linkage to provisions)  │
├─────────────────────────────────────────────────────────────────┤
│ kg_relationships (complex semantic relationships)              │
│ ├─ subject_entity_id ←→ object_entity_id                       │
│ ├─ predicate (relationship type)                               │
│ └─ context (document_id, page_number)                          │
├─────────────────────────────────────────────────────────────────┤
│ clause_relationships (provision hierarchy)                     │
│ └─ parent_provision_id ←→ child_provision_id                   │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    VISUAL CONTENT LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│ kg_visual_elements (images, diagrams, tables)                  │
│ ├─ visual_type, image_path, extracted_content                  │
│ └─ page_number, document_id                                     │
├─────────────────────────────────────────────────────────────────┤
│ kg_visual_clause_links (image ←→ provision linkage)            │
│ ├─ visual_element_id → clause_reference                        │
│ ├─ illustration_type, confidence_score                         │
│ └─ original_ref_type, original_ref_id                          │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    PROVISIONS LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│ regulatory_provisions (17,849+ provisions)                     │
│ ├─ zone, development_type, provision_text                      │
│ ├─ document_id, section_header, ref_number                     │
│ └─ domain_classification, prp_k1_enhanced                      │
├─────────────────────────────────────────────────────────────────┤
│ quantitative_standards (numeric values)                        │
│ ├─ provision_id → numeric_value, unit, context                 │
│ └─ confidence_score                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Current Entity Coverage

The existing AutoSchemaKG entities provide:
- **Entity Types**: ZONE, DEVELOPMENT_TYPE, SETBACK_RULE, SITE_COVERAGE, HEIGHT_LIMIT, etc.
- **Relationships**: "applies_to", "overrides", "requires", "permits", "restricts"
- **Visual Links**: Images showing setback diagrams, zone maps, building forms
- **Document Traceability**: Full provenance from PDF page to final provision

### Gaps in Current Architecture

1. **Missing Zone Coverage**: Only some zones have full entity extraction
2. **Incomplete Development Type Mapping**: C11 provisions were missing entities
3. **Visual Element Orphaning**: Some images lack provision linkage
4. **Relationship Incompleteness**: Cross-zone relationships not fully captured

## PRP-K7 Enhanced Import Strategy

### Problem: Naive Import Would Break Entity Relationships

If we simply import new provisions without considering the existing AutoSchemaKG structure, we would:
- ❌ Create orphaned provisions with no entity relationships
- ❌ Break visual element linkages
- ❌ Lose semantic relationships between zones and development types
- ❌ Duplicate entities that already exist in different forms

### Solution: Entity-Aware Import Pipeline

```python
# Enhanced PRP-K7 Import Architecture
class EntityAwareZoneImporter:
    """Import that preserves and extends existing AutoSchemaKG relationships"""
    
    def __init__(self):
        self.existing_entities = self.load_existing_entities()
        self.existing_relationships = self.load_existing_relationships()
        self.visual_mappings = self.load_visual_mappings()
        
    def import_zone_with_entities(self, zone_provisions: List[Dict]) -> Dict:
        """Import provisions while preserving/extending entity relationships"""
        
        results = {
            'provisions_imported': 0,
            'entities_created': 0,
            'entities_linked': 0,
            'relationships_created': 0,
            'visual_links_created': 0
        }
        
        for provision in zone_provisions:
            # 1. Import provision (as before)
            provision_id = self.import_provision(provision)
            
            # 2. Create/link entities
            entities = self.extract_or_link_entities(provision)
            
            # 3. Create semantic relationships
            relationships = self.create_entity_relationships(entities)
            
            # 4. Link visual elements
            visual_links = self.link_visual_elements(provision, entities)
            
            # 5. Update parent-child clause relationships
            clause_rels = self.update_clause_hierarchy(provision_id, provision)
            
            # Update counters
            results['provisions_imported'] += 1
            results['entities_created'] += len([e for e in entities if e['action'] == 'created'])
            results['entities_linked'] += len([e for e in entities if e['action'] == 'linked'])
            results['relationships_created'] += len(relationships)
            results['visual_links_created'] += len(visual_links)
            
        return results
    
    def extract_or_link_entities(self, provision: Dict) -> List[Dict]:
        """Extract entities from provision or link to existing ones"""
        entities = []
        
        # Zone entity
        zone_entity = self.get_or_create_entity(
            entity_type='ZONE',
            entity_name=provision['zone'],
            entity_description=f"Planning zone {provision['zone']}",
            source_provision_id=provision['id']
        )
        entities.append(zone_entity)
        
        # Development type entity
        if provision['development_type']:
            dev_type_entity = self.get_or_create_entity(
                entity_type='DEVELOPMENT_TYPE',
                entity_name=provision['development_type'],
                entity_description=self.get_dev_type_description(provision['development_type']),
                source_provision_id=provision['id']
            )
            entities.append(dev_type_entity)
        
        # Setback entities (front, side, rear)
        for setback_type, value in provision.get('setbacks', {}).items():
            setback_entity = self.get_or_create_entity(
                entity_type='SETBACK_REQUIREMENT',
                entity_name=f"{provision['zone']}_{provision['development_type']}_{setback_type}",
                entity_description=f"{setback_type.title()} setback: {value}m for {provision['development_type']} in zone {provision['zone']}",
                source_provision_id=provision['id']
            )
            entities.append(setback_entity)
        
        return entities
    
    def create_entity_relationships(self, entities: List[Dict]) -> List[Dict]:
        """Create semantic relationships between entities"""
        relationships = []
        
        zone_entity = next((e for e in entities if e['type'] == 'ZONE'), None)
        dev_type_entity = next((e for e in entities if e['type'] == 'DEVELOPMENT_TYPE'), None)
        setback_entities = [e for e in entities if e['type'] == 'SETBACK_REQUIREMENT']
        
        if zone_entity and dev_type_entity:
            # Zone permits development type
            relationships.append({
                'subject_entity_id': zone_entity['id'],
                'predicate': 'permits',
                'object_entity_id': dev_type_entity['id'],
                'relationship_context': 'Planning permission'
            })
        
        if dev_type_entity and setback_entities:
            for setback_entity in setback_entities:
                # Development type requires setback
                relationships.append({
                    'subject_entity_id': dev_type_entity['id'],
                    'predicate': 'requires',
                    'object_entity_id': setback_entity['id'],
                    'relationship_context': 'Building regulation'
                })
        
        # Cross-zone relationships (if applicable)
        relationships.extend(self.create_cross_zone_relationships(zone_entity, entities))
        
        return relationships
    
    def link_visual_elements(self, provision: Dict, entities: List[Dict]) -> List[Dict]:
        """Link visual elements (images, diagrams) to new provisions"""
        visual_links = []
        
        # Find related visual elements by document and page
        related_visuals = self.find_visual_elements(
            document_id=provision['document_id'],
            page_number=provision.get('page_number'),
            zone=provision['zone'],
            development_type=provision.get('development_type')
        )
        
        for visual in related_visuals:
            # Create link between visual element and provision
            link = {
                'visual_element_id': visual['id'],
                'clause_reference': provision.get('ref_number', f"Provision {provision['id']}"),
                'illustration_type': self.determine_illustration_type(visual, provision),
                'confidence_score': self.calculate_visual_confidence(visual, provision)
            }
            visual_links.append(link)
            
            # Also link to relevant entities
            for entity in entities:
                if entity['type'] in ['SETBACK_REQUIREMENT', 'DEVELOPMENT_TYPE']:
                    entity_visual_link = {
                        'entity_id': entity['id'],
                        'visual_element_id': visual['id'],
                        'link_type': 'illustrates',
                        'confidence': link['confidence_score']
                    }
                    visual_links.append(entity_visual_link)
        
        return visual_links
    
    def update_clause_hierarchy(self, provision_id: int, provision: Dict) -> List[Dict]:
        """Update parent-child relationships between clauses"""
        relationships = []
        
        # Find parent clauses (e.g., C11 is parent of C11 i, C11 ii, etc.)
        parent_ref = self.extract_parent_reference(provision.get('ref_number', ''))
        if parent_ref:
            parent_provision = self.find_provision_by_reference(parent_ref)
            if parent_provision:
                relationships.append({
                    'parent_provision_id': parent_provision['id'],
                    'child_provision_id': provision_id,
                    'relationship_type': 'contains',
                    'confidence_score': 0.95
                })
        
        # Find child clauses
        child_refs = self.find_child_references(provision.get('ref_number', ''))
        for child_ref in child_refs:
            child_provision = self.find_provision_by_reference(child_ref)
            if child_provision:
                relationships.append({
                    'parent_provision_id': provision_id,
                    'child_provision_id': child_provision['id'],
                    'relationship_type': 'contains',
                    'confidence_score': 0.95
                })
        
        return relationships
```

### Post-Import Database Architecture

After PRP-K7 implementation, the database will have:

```
ENHANCED ARCHITECTURE POST PRP-K7:
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE GRAPH LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│ kg_entities (15,000+ entities - 50% increase)                  │
│ ├─ Zone entities: R1, R2, R3, R4, B1, B2, B4, B6, etc.        │
│ ├─ Development type entities: multi_dwelling, RFB, etc.        │
│ ├─ Setback requirement entities: zone+devtype+boundary         │
│ └─ Cross-references maintained to original sources             │
├─────────────────────────────────────────────────────────────────┤
│ kg_relationships (enhanced with zone relationships)            │
│ ├─ Zone PERMITS Development_Type                               │
│ ├─ Development_Type REQUIRES Setback_Requirement              │
│ ├─ Setback_Requirement APPLIES_TO Boundary_Type               │
│ ├─ Zone OVERRIDES Other_Zone (SEPP relationships)             │
│ └─ Development_Type CONFLICTS_WITH Other_Dev_Type             │
├─────────────────────────────────────────────────────────────────┤
│ clause_relationships (complete hierarchy)                      │
│ ├─ C11 contains C11.i, C11.ii, C11.iii                       │
│ ├─ C12 contains C12.v, C12.vi                                 │
│ └─ Section 4.2.4.3 contains all building setback clauses     │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    VISUAL CONTENT LAYER                         │
├─────────────────────────────────────────────────────────────────┤
│ kg_visual_elements (unchanged - existing images preserved)     │
├─────────────────────────────────────────────────────────────────┤
│ kg_visual_clause_links (enhanced linkage)                      │
│ ├─ Existing links preserved                                    │
│ ├─ New provisions linked to relevant diagrams                 │
│ ├─ Multi-zone diagrams linked to multiple provisions          │
│ └─ Confidence scores for visual-text correlation              │
├─────────────────────────────────────────────────────────────────┤
│ kg_entity_visual_links (NEW TABLE)                            │
│ ├─ Entity-level visual linkage                                │
│ ├─ Setback diagrams → Setback_Requirement entities           │
│ └─ Zone maps → Zone entities                                   │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│                    PROVISIONS LAYER (ENHANCED)                  │
├─────────────────────────────────────────────────────────────────┤
│ regulatory_provisions (25,000+ provisions - complete zones)    │
│ ├─ ALL zones covered: R1-R4, B1-B6, IN1-IN2, E2-E3, RE1-RE2  │
│ ├─ ALL development types per zone                              │
│ ├─ Complete entity linkage via kg_entities                     │
│ └─ Full provenance preservation                                │
├─────────────────────────────────────────────────────────────────┤
│ quantitative_standards (tripled - all setback values)         │
│ ├─ Zone-specific standards                                     │
│ ├─ Development-type-specific standards                         │
│ └─ Boundary-type-specific standards                            │
├─────────────────────────────────────────────────────────────────┤
│ zone_development_matrix (NEW TABLE)                           │
│ ├─ zone_id, development_type, permitted (boolean)             │
│ ├─ Fast lookup for UI progressive disclosure                  │
│ └─ Sourced from LEP analysis                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Strategy

#### Phase 1: Entity-Relationship Preservation
1. **Audit existing entities** before import
2. **Map JSON sources** to existing visual elements
3. **Identify entity overlap** to prevent duplication
4. **Preserve visual-provision links** during import

#### Phase 2: Enhanced Import Pipeline
```python
# Usage example
importer = EntityAwareZoneImporter()

# Import with full entity relationship preservation
results = importer.import_all_zones_with_entities()

# Verify entity integrity
verifier = EntityRelationshipVerifier()
integrity_report = verifier.verify_post_import()
```

#### Phase 3: Cross-Zone Relationship Mining
1. **Detect zone interactions** (e.g., R2/R3 boundary effects)
2. **Map development type transitions** (e.g., RFB permitted in both R2 and R3)
3. **Link shared visual elements** across zones
4. **Create authority hierarchy links** (SEPP > LEP > DCP)

### Benefits of Entity-Aware Import

1. **Preserved Intelligence**: Existing AutoSchemaKG relationships maintained
2. **Enhanced Queryability**: Can query "Show all zones that permit RFBs with images"
3. **Visual Correlation**: Images automatically linked to relevant new provisions
4. **Semantic Search**: "Find setback diagrams for multi-dwelling housing" works
5. **Compliance Traceability**: Full audit trail from image → entity → provision
6. **Cross-Zone Analysis**: Compare requirements across zones with visual support

### Risk Mitigation

1. **Backup Strategy**: Full database backup before import
2. **Incremental Import**: Import one zone at a time with verification
3. **Rollback Capability**: Track all entity/relationship IDs created
4. **Duplicate Detection**: Prevent entity duplication through fuzzy matching
5. **Visual Integrity Checks**: Ensure no orphaned visual elements

### Success Metrics

Post-import verification should confirm:
- ✅ All existing entities and relationships preserved
- ✅ New entities properly linked to existing knowledge graph
- ✅ Visual elements maintain their provision linkages
- ✅ No orphaned entities or relationships created
- ✅ Cross-zone queries return expected results
- ✅ Zone-development type matrix populated
- ✅ UI can query entity relationships for progressive disclosure

This approach ensures PRP-K7 enhances rather than disrupts the sophisticated knowledge architecture already built into the system.