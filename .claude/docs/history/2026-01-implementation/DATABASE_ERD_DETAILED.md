# DETAILED ENTITY-RELATIONSHIP DIAGRAM
**NSW Planning Compliance Engine Database**

## COMPLETE TABLE RELATIONSHIP MAP

```
================================================================================
                    CORE REGULATORY PROVISION FLOW
================================================================================

                        ┌─────────────────────────────┐
                        │     documents (274)         │
                        │  ┌───────────────────────┐  │
                        │  │ id (TEXT) <NO PK!>    │  │
                        │  │ pdf_name              │  │
                        │  │ document_type         │  │
                        │  │ document_area         │  │
                        │  │ full_text (TEXT)      │  │
                        │  └───────────────────────┘  │
                        └──────────┬──────────────────┘
                                   │
                                   │ (conceptual link, no FK)
                                   │
                                   ▼
        ┌──────────────────────────────────────────────────────────────┐
        │         regulatory_provisions (22,648)                       │
        │  ┌────────────────────────────────────────────────────────┐  │
        │  │ id (PK) SERIAL                                         │  │
        │  │ document_id TEXT                                       │  │
        │  │ provision_type TEXT                                    │  │
        │  │ ref_number TEXT                                        │  │
        │  │ provision_text TEXT                                    │  │
        │  │ zone TEXT (nullable)                                   │  │
        │  │ development_type TEXT                                  │  │
        │  │ page_number TEXT                                       │  │
        │  │ section_header TEXT                                    │  │
        │  │ text_level TEXT                                        │  │
        │  │─────────────────────────────────────────────────────  │  │
        │  │ is_canonical BOOLEAN DEFAULT TRUE                      │  │
        │  │ canonical_provision_id INTEGER ───┐ (self-reference)  │  │
        │  │ text_hash TEXT (MD5)              │                    │  │
        │  │ migration_phase TEXT               │                    │  │
        │  │─────────────────────────────────────────────────────  │  │
        │  │ cross_reference_text TEXT                              │  │
        │  │ provision_category TEXT                                │  │
        │  │ display_priority INTEGER DEFAULT 5                     │  │
        │  │ is_mandatory BOOLEAN DEFAULT TRUE                      │  │
        │  │─────────────────────────────────────────────────────  │  │
        │  │ created_at TEXT                                        │  │
        │  │ last_updated TIMESTAMP DEFAULT NOW()                   │  │
        │  └────────────────────────────────────────────────────────┘  │
        └────┬──────────────┬────────────────┬─────────────┬──────────┘
             │              │                │             │
             │              │                │             │
   ┌─────────┘              │                │             └───────────┐
   │                        │                │                         │
   │                        │                │                         │
   ▼                        ▼                ▼                         ▼

┌──────────────────┐  ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
│provision_        │  │control_codes │  │cross_reference_ │  │provision_    │
│applicability     │  │(24,346)      │  │index (3,801)    │  │diagrams      │
│(22,979)          │  │              │  │                 │  │(0 - future)  │
│                  │  │              │  │                 │  │              │
│┌────────────────┐│  │┌────────────┐│  │┌───────────────┐│  │┌────────────┐│
││id (PK) SERIAL  ││  ││id (PK)     ││  ││id (PK) SERIAL ││  ││id (PK)     ││
││                ││  ││            ││  ││               ││  ││            ││
││provision_id◄───┼┼──┼┤provision_id◄┼──┼┤source_prov_id◄┼──┼┤provision_id││
││  FK CASCADE    ││  ││  FK CASCADE││  ││  FK CASCADE   ││  ││  FK CASCADE││
││                ││  ││            ││  ││               ││  ││            ││
││applies_to_zone ││  ││code        ││  ││reference_type ││  ││visual_elem_││
││applies_to_all_ ││  ││code_group  ││  ││reference_num  ││  ││  id (TEXT) ││
││  zones BOOLEAN ││  ││control_type││  ││reference_text ││  ││diagram_num ││
││applies_state_  ││  ││sequence_num││  ││               ││  ││is_required ││
││  wide BOOLEAN  ││  ││is_range_   ││  ││target_prov_id?┼──┐││link_method ││
││applies_to_lga  ││  ││  start BOOL││  ││  FK MISSING!  ││ │││confidence  ││
││excluded_zones[]││  ││is_range_   ││  ││               ││ │││manually_   ││
││applicability_  ││  ││  end BOOL  ││  ││resolution_    ││ │││  verified  ││
││  source        ││  ││            ││  ││  status       ││ │││            ││
││confidence_score││  ││created_at  ││  ││resolution_    ││ │││created_at  ││
││notes           ││  ││            ││  ││  confidence   ││ │││            ││
││created_at      ││  │└────────────┘│  ││is_mandatory   ││ ││└────────────┘│
│└────────────────┘│  │              │  ││context_snippet││ │└──────────────┘
│                  │  │UNIQUE:       │  ││               ││ │
│INDEXES:          │  │  (code,      │  ││created_at     ││ │
│  provision_id    │  │   provision) │  ││updated_at     ││ │
│  zone            │  │              │  │└───────────────┘│ │
│  all_zones       │  │INDEXES:      │  │                 │ │
│  state_wide      │  │  code        │  │INDEXES:         │ │ (self-FK)
│  lga             │  │  provision   │  │  source_prov    │ │ for cross-
└──────────────────┘  │  type        │  │  target_prov    │ │ reference
                      │  group       │  │  number         │ │ resolution
                      └──────────────┘  │  type           │ │
                                        │  status         │ │
                                        │  type+number    │ │
                                        └─────────────────┘ │
                                                            │
                                        ┌───────────────────┘
                                        │
                      ┌─────────────────▼─────────────────────┐
                      │  (back to regulatory_provisions)      │
                      │  target resolution links to same      │
                      │  table for cross-reference resolution │
                      └───────────────────────────────────────┘

================================================================================
              EXTRACTED DEVELOPMENT CONTROL DATA
================================================================================

  From regulatory_provisions → Extract numeric/quantitative values

┌──────────────────────────────┐        ┌──────────────────────────────┐
│  development_controls        │        │  quantitative_standards      │
│  (4,508 rows)                │        │  (832 rows)                  │
│                              │        │                              │
│  ┌────────────────────────┐  │        │  ┌────────────────────────┐  │
│  │ id (PK) SERIAL         │  │        │  │ id (PK) SERIAL         │  │
│  │                        │  │        │  │                        │  │
│  │ provision_id TEXT!!!   │  │        │  │ provision_id TEXT!!!   │  │
│  │   (should be INT FK)   │  │        │  │   (should be INT FK)   │  │
│  │                        │  │        │  │                        │  │
│  │ control_type TEXT      │  │        │  │ standard_type TEXT     │  │
│  │ control_subtype TEXT   │  │        │  │ numeric_value TEXT!!!  │  │
│  │ value_numeric TEXT!!!  │  │        │  │ unit TEXT              │  │
│  │ value_text TEXT        │  │        │  │ qualifier TEXT         │  │
│  │ unit TEXT              │  │        │  │ context TEXT           │  │
│  │ zone_applicable TEXT   │  │        │  │ applies_to_zone TEXT   │  │
│  │ conditions TEXT        │  │        │  │ applies_to_dev_type    │  │
│  │ confidence_score TEXT!!│  │        │  │ confidence_score TEXT!!│  │
│  │ extraction_method      │  │        │  │ extracted_from_text    │  │
│  └────────────────────────┘  │        │  └────────────────────────┘  │
│                              │        │                              │
│  ISSUES:                     │        │  ISSUES:                     │
│  ✗ provision_id is TEXT      │        │  ✗ provision_id is TEXT      │
│  ✗ value_numeric is TEXT     │        │  ✗ numeric_value is TEXT     │
│  ✗ confidence_score is TEXT  │        │  ✗ confidence_score is TEXT  │
│  ✗ NO Foreign Keys!          │        │  ✗ NO Foreign Keys!          │
│  ✗ Only PK index             │        │  ✗ Only PK index             │
└──────────────────────────────┘        └──────────────────────────────┘

         Both should have:
         - provision_id INTEGER FK → regulatory_provisions(id) CASCADE
         - value fields as DECIMAL(10,2)
         - confidence_score as DECIMAL(3,2)
         - Indexes on provision_id, zone, type

================================================================================
                    KNOWLEDGE GRAPH STRUCTURE
================================================================================

┌─────────────────────────────┐              ┌───────────────────────────────┐
│  kg_entities (16)           │              │  kg_relationships (17)        │
│                             │              │                               │
│  ┌───────────────────────┐  │              │  ┌─────────────────────────┐  │
│  │ id (PK) SERIAL        │◄─┼──────────────┼──┤ subject_entity_id TEXT!!│  │
│  │                       │  │              │  │   (should be INT FK)    │  │
│  │ entity_name TEXT      │  │              │  │                         │  │
│  │ entity_type TEXT      │  │              │  │ predicate TEXT          │  │
│  │ entity_subtype TEXT   │  │              │  │                         │  │
│  │ entity_value TEXT     │  │              │  │ object_entity_id TEXT!! │  │
│  │                       │◄─┼──────────────┼──┤   (should be INT FK)    │  │
│  │ document_id TEXT      │  │              │  │                         │  │
│  │ page_number TEXT      │  │              │  │ subject_text TEXT       │  │
│  │ section_header TEXT   │  │              │  │ object_text TEXT        │  │
│  │ text_snippet TEXT     │  │              │  │                         │  │
│  │ confidence_score TEXT!│  │              │  │ relationship_context    │  │
│  │                       │  │              │  │ document_id TEXT        │  │
│  │ normalization_status  │  │              │  │ page_number TEXT        │  │
│  │ canonical_entity_id   │  │              │  │ confidence_score TEXT!! │  │
│  │ original_ref_id       │  │              │  │                         │  │
│  │ extraction_timestamp  │  │              │  │ original_ref_type       │  │
│  └───────────────────────┘  │              │  │ original_ref_id         │  │
│                             │              │  │ extraction_timestamp    │  │
│  INDEXES:                   │              │  └─────────────────────────┘  │
│    Only PK                  │              │                               │
│                             │              │  INDEXES:                     │
│  ISSUES:                    │              │    Only PK                    │
│  ✗ Only 16 entities!        │              │                               │
│  ✗ confidence_score TEXT    │              │  ISSUES:                      │
│  ✗ No indexes               │              │  ✗ Only 17 relationships!     │
│  ✗ No FK to documents       │              │  ✗ entity_id fields are TEXT  │
└─────────────────────────────┘              │  ✗ No Foreign Keys!           │
                                             │  ✗ confidence_score TEXT      │
                                             └───────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  kg_relationships_from_refs (2,294) - MUCH MORE COMPLETE                   │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ id (PK) SERIAL                                                        │ │
│  │ relationship_type TEXT                                                │ │
│  │ subject_text TEXT                                                     │ │
│  │ predicate TEXT                                                        │ │
│  │ object_text TEXT                                                      │ │
│  │ document_id TEXT                                                      │ │
│  │ page_number TEXT                                                      │ │
│  │ ref_number TEXT                                                       │ │
│  │ provision_text TEXT (DUPLICATE DATA!)                                 │ │
│  │ source_ref_id TEXT (should FK to regulatory_refs)                     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  NOTE: This table has 135x more relationships than kg_relationships!       │
│        Suggests KG extraction incomplete or this is the real KG data.      │
└────────────────────────────────────────────────────────────────────────────┘

================================================================================
                    VISUAL & CONTEXTUAL CONTENT
================================================================================

┌──────────────────────────────┐        ┌──────────────────────────────┐
│  visual_elements_real        │        │  contextual_guidance_real    │
│  (3,017 images/diagrams)     │        │  (6,655 guidance texts)      │
│                              │        │                              │
│  ┌────────────────────────┐  │        │  ┌────────────────────────┐  │
│  │ id TEXT <NO PK!>       │  │        │  │ id TEXT <NO PK!>       │  │
│  │ document_id TEXT       │  │        │  │ document_id TEXT       │  │
│  │ element_type TEXT      │  │        │  │ guidance_type TEXT     │  │
│  │ element_title TEXT     │  │        │  │ guidance_title TEXT    │  │
│  │ page_number TEXT       │  │        │  │ guidance_text TEXT     │  │
│  │ section_header TEXT    │  │        │  │ page_number TEXT       │  │
│  │ bbox TEXT              │  │        │  │ section_header TEXT    │  │
│  │ image_path TEXT        │  │        │  │ text_level TEXT        │  │
│  │ image_data TEXT        │  │        │  │ category TEXT          │  │
│  │ image_hash TEXT        │  │        │  └────────────────────────┘  │
│  │ caption_text TEXT      │  │        │                              │
│  │ ocr_text TEXT          │  │        │  ISSUES:                     │
│  │ width TEXT!!!          │  │        │  ✗ No Primary Key            │
│  │ height TEXT!!!         │  │        │  ✗ No Foreign Keys           │
│  └────────────────────────┘  │        │  ✗ No Indexes                │
│                              │        └──────────────────────────────┘
│  ISSUES:                     │
│  ✗ No Primary Key            │        ┌──────────────────────────────┐
│  ✗ width/height are TEXT!    │        │  visual_elements (1,473)     │
│  ✗ No Foreign Keys           │        │  - Possibly older version?   │
│  ✗ No Indexes                │        │  - Same structure            │
└──────────────────────────────┘        └──────────────────────────────┘
         ▲
         │ (intended FK via provision_diagrams, not yet implemented)
         │
         └─────── provision_diagrams (0 rows)
                  Table exists but empty
                  Future: Link provisions to visual elements

================================================================================
                    PERMISSION & PERMISSIBILITY DATA
================================================================================

┌──────────────────────────────┐        ┌──────────────────────────────┐
│  permissibility_analysis     │        │  development_permissions     │
│  (958 rows)                  │        │  (246 rows)                  │
│                              │        │                              │
│  ┌────────────────────────┐  │        │  ┌────────────────────────┐  │
│  │ id (PK) SERIAL         │  │        │  │ id (PK) SERIAL         │  │
│  │ zone TEXT              │  │        │  │ zone TEXT              │  │
│  │ development_type TEXT  │  │        │  │ development_type TEXT  │  │
│  │ permission_status TEXT │  │        │  │ permission_status TEXT │  │
│  │ permission_category    │  │        │  │ source_document        │  │
│  │ source_document        │  │        │  │ source_clause          │  │
│  │ source_clause          │  │        │  │ additional_conditions  │  │
│  │ conditions TEXT        │  │        │  │ confidence_score TEXT!!│  │
│  │ created_at TEXT        │  │        │  │ extraction_method      │  │
│  └────────────────────────┘  │        │  └────────────────────────┘  │
│                              │        │                              │
│  NOTE: Overlapping purpose   │        │  NOTE: Similar to left table │
│        Should consolidate?   │        │        Consolidate?          │
└──────────────────────────────┘        └──────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  development_pathways (1 row)                                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ id (PK) SERIAL                                                        │ │
│  │ pathway_type TEXT ('exempt', 'complying_development', 'da_required')  │ │
│  │ development_type TEXT                                                 │ │
│  │ zone TEXT                                                             │ │
│  │ key_requirements TEXT                                                 │ │
│  │ prohibitions TEXT                                                     │ │
│  │ additional_standards TEXT                                             │ │
│  │ source_sepp TEXT                                                      │ │
│  │ source_lep TEXT                                                       │ │
│  │ source_dcp TEXT                                                       │ │
│  │ notes TEXT                                                            │ │
│  │ created_at TIMESTAMP DEFAULT NOW()                                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  NOTE: Only 1 row - incomplete or test data                                │
└────────────────────────────────────────────────────────────────────────────┘

================================================================================
                    HIERARCHY & OVERRIDE RESOLUTION
================================================================================

┌────────────────────────────────────────────────────────────────────────────┐
│  sepp_lep_overrides (91 rows)                                              │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ id (PK) SERIAL                                                        │ │
│  │                                                                       │ │
│  │ sepp_provision_id TEXT!!! (should be INT FK)                          │ │
│  │   ────────────────────────? (no FK constraint!)                       │ │
│  │                                                                       │ │
│  │ lep_provision_id TEXT!!! (should be INT FK)                           │ │
│  │   ────────────────────────? (no FK constraint!)                       │ │
│  │                                                                       │ │
│  │ override_type TEXT ('full_override', 'partial_override', 'supplement')│ │
│  │ override_reason TEXT                                                  │ │
│  │ sepp_clause TEXT                                                      │ │
│  │ lep_clause TEXT                                                       │ │
│  │ resolution_rule TEXT                                                  │ │
│  │ confidence_score TEXT!!! (should be DECIMAL)                          │ │
│  │ verified_by TEXT                                                      │ │
│  │ created_at TIMESTAMP DEFAULT NOW()                                    │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  CRITICAL ISSUES:                                                          │
│  ✗ sepp_provision_id and lep_provision_id are TEXT (should be INTEGER)    │
│  ✗ NO Foreign Key constraints to regulatory_provisions                    │
│  ✗ confidence_score is TEXT (should be DECIMAL)                           │
│  ✗ No indexes except PK                                                   │
│                                                                             │
│  SHOULD HAVE:                                                              │
│  ✓ sepp_provision_id INTEGER FK → regulatory_provisions(id)               │
│  ✓ lep_provision_id INTEGER FK → regulatory_provisions(id)                │
│  ✓ confidence_score DECIMAL(3,2)                                          │
│  ✓ INDEX on sepp_provision_id, lep_provision_id                           │
└────────────────────────────────────────────────────────────────────────────┘

================================================================================
                    LEGACY / REFERENCE TABLES
================================================================================

┌──────────────────────────────┐        ┌──────────────────────────────┐
│  regulatory_refs             │        │  regulatory_refs_core        │
│  (2,698 rows)                │        │  (762 rows - subset?)        │
│                              │        │                              │
│  Similar structure to        │        │  Similar structure to        │
│  regulatory_provisions       │        │  regulatory_refs             │
│                              │        │                              │
│  Possibly pre-migration      │        │  Possibly filtered subset    │
│  legacy data                 │        │  or "core" provisions        │
│                              │        │                              │
│  No clear FK relationship    │        │  No clear FK relationship    │
│  to regulatory_provisions    │        │  to either table             │
└──────────────────────────────┘        └──────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│  MISCELLANEOUS TABLES                                                      │
│                                                                             │
│  • zone_setback_rules (6) - Simple zone setback data                       │
│  • zone_setback_rules_comprehensive_archived (0) - Empty archive           │
│  • table_parsing_results (63) - Table extraction results                   │
│  • verification_tests (17) - Test cases                                    │
│  • verified_compliance_rules (6) - Manually verified rules                 │
│  • quality_metrics (6) - Data quality scores                               │
│  • sqlite_sequence (13) - SQLite internal (can be dropped in PostgreSQL)   │
│  • sqlite_stat1 (52) - SQLite internal (can be dropped in PostgreSQL)      │
└────────────────────────────────────────────────────────────────────────────┘

================================================================================
                    VIEWS (Denormalized Query Helpers)
================================================================================

regulatory_provisions_canonical
  └─► SELECT * FROM regulatory_provisions WHERE is_canonical = TRUE
      (Filters out duplicates)

provisions_with_applicability
  └─► JOIN regulatory_provisions + provision_applicability
      (Denormalized zone applicability)

provisions_with_control_codes
  └─► JOIN regulatory_provisions + control_codes with array_agg
      (Provisions with exploded codes as arrays)

provisions_with_cross_refs
  └─► JOIN regulatory_provisions + cross_reference_index with json_agg
      (Provisions with cross-references as JSON)

provisions_with_category
  └─► SELECT * FROM regulatory_provisions
      (Alias view, includes all columns)

================================================================================
                    FOREIGN KEY SUMMARY
================================================================================

✓ ENFORCED Foreign Keys:
  • control_codes.provision_id → regulatory_provisions(id) CASCADE
  • provision_applicability.provision_id → regulatory_provisions(id) CASCADE
  • cross_reference_index.source_provision_id → regulatory_provisions(id) CASCADE
  • provision_diagrams.provision_id → regulatory_provisions(id) CASCADE
  • regulatory_provisions.canonical_provision_id → regulatory_provisions(id) SET NULL

✗ MISSING Foreign Keys (should be added):
  • documents.id → (no FK from regulatory_provisions.document_id)
  • development_controls.provision_id → regulatory_provisions(id)
  • quantitative_standards.provision_id → regulatory_provisions(id)
  • kg_relationships.subject_entity_id → kg_entities(id)
  • kg_relationships.object_entity_id → kg_entities(id)
  • kg_relationships_from_refs.source_ref_id → regulatory_refs(id)
  • sepp_lep_overrides.sepp_provision_id → regulatory_provisions(id)
  • sepp_lep_overrides.lep_provision_id → regulatory_provisions(id)
  • cross_reference_index.target_provision_id → regulatory_provisions(id)
  • provision_diagrams.visual_element_id → visual_elements_real(id)

================================================================================
                    DATA TYPE ISSUES
================================================================================

CRITICAL (Numeric fields stored as TEXT):
  ✗ documents.char_count, word_count → should be INTEGER
  ✗ development_controls.provision_id → should be INTEGER
  ✗ development_controls.value_numeric → should be DECIMAL(10,2)
  ✗ development_controls.confidence_score → should be DECIMAL(3,2)
  ✗ quantitative_standards.provision_id → should be INTEGER
  ✗ quantitative_standards.numeric_value → should be DECIMAL(10,2)
  ✗ quantitative_standards.confidence_score → should be DECIMAL(3,2)
  ✗ visual_elements_real.width, height → should be INTEGER
  ✗ kg_entities.confidence_score → should be DECIMAL(3,2)
  ✗ kg_relationships.confidence_score → should be DECIMAL(3,2)
  ✗ kg_relationships.subject_entity_id, object_entity_id → should be INTEGER
  ✗ sepp_lep_overrides.sepp_provision_id → should be INTEGER
  ✗ sepp_lep_overrides.lep_provision_id → should be INTEGER
  ✗ sepp_lep_overrides.confidence_score → should be DECIMAL(3,2)

ALL confidence_score columns should be DECIMAL(3,2) CHECK (0.0 <= value <= 1.0)

================================================================================
```

## RELATIONSHIP CARDINALITY

```
regulatory_provisions (1) ───< (N) provision_applicability
regulatory_provisions (1) ───< (N) control_codes
regulatory_provisions (1) ───< (N) cross_reference_index (source)
regulatory_provisions (1) ───< (N) cross_reference_index (target)
regulatory_provisions (1) ───< (N) provision_diagrams
regulatory_provisions (1) ───? (N) development_controls (FK missing)
regulatory_provisions (1) ───? (N) quantitative_standards (FK missing)
regulatory_provisions (1) ──>  (1) regulatory_provisions (self-ref canonical)

documents (1) ───? (N) regulatory_provisions (conceptual, no FK)
kg_entities (1) ───? (N) kg_relationships (FK missing)
kg_entities (1) ───? (N) kg_relationships (FK missing - object)
visual_elements_real (1) ───? (N) provision_diagrams (FK can't be added - type mismatch)
```

## PRIMARY KEY ISSUES

Tables WITHOUT enforced primary keys:
- documents (id is TEXT nullable)
- visual_elements_real (id is TEXT nullable)
- contextual_guidance_real (id is TEXT nullable)
- All views (views don't have PKs)

## INDEX COVERAGE ANALYSIS

```
EXCELLENT (6+ indexes):
  ✓ regulatory_provisions (12 indexes)
  ✓ cross_reference_index (6 indexes)
  ✓ provision_applicability (6 indexes)
  ✓ control_codes (6 indexes)

GOOD (3-5 indexes):
  ✓ provision_diagrams (4 indexes) - but table is empty

MINIMAL (1-2 indexes):
  ○ development_controls (1 - PK only)
  ○ All other tables with SERIAL PK

NONE (0 indexes):
  ✗ documents
  ✗ visual_elements_real
  ✗ contextual_guidance_real
  ✗ kg_entities (except PK)
  ✗ kg_relationships (except PK)
  ✗ quantitative_standards (except PK)
  ✗ permissibility_analysis (except PK)
```

---

*This ERD shows the complete structure of the NSW Planning Compliance Engine database with all relationships, issues, and recommendations.*
