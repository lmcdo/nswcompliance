# NSW Planning Database Architecture (PRP Pattern)

## Overview
The NSW Planning Database follows the **PRP (Provisions, Relationships, Pathways)** architecture pattern with entities and relationships integration. This document details all 21 tables and their role in the compliance engine.

## Core Architecture Pattern

```
PROVISIONS ↔ RELATIONSHIPS ↔ PATHWAYS
     ↓            ↓            ↓
  ENTITIES ←→ KG_GRAPH ←→ CONTROLS
```

---

## 1. PROVISIONS LAYER (Legal Text Storage)

### regulatory_provisions_clean
**Purpose**: Core cleaned regulatory provisions from planning documents
**Rows**: 9,364
```sql
CREATE TABLE regulatory_provisions_clean (
  id INT PRIMARY KEY,
  document_id TEXT,           -- Links to documents table
  provision_type TEXT,        -- clause|section|schedule
  ref_number TEXT,           -- 9.34, 4.1.2, etc.
  provision_text TEXT,       -- Full legal text
  page_number INT,
  section_header TEXT,
  text_level INT,            -- Hierarchy depth
  category TEXT
);
```

### regulatory_provisions  
**Purpose**: Original unprocessed provisions with metadata
**Rows**: 22,092
```sql
CREATE TABLE regulatory_provisions (
  id INTEGER PRIMARY KEY,
  document_id TEXT NOT NULL,
  provision_type TEXT NOT NULL,
  ref_number TEXT,
  provision_text TEXT NOT NULL,
  zone TEXT,                 -- R2, B4, etc.
  development_type TEXT,
  page_number INTEGER,
  section_header TEXT,
  text_level INTEGER,
  original_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### documents
**Purpose**: Source document metadata and full text
**Rows**: 274
```sql
CREATE TABLE documents (
  id TEXT PRIMARY KEY,       -- Document identifier
  pdf_name TEXT NOT NULL,    -- Original filename
  document_type TEXT NOT NULL, -- LEP, DCP, SEPP
  document_area TEXT,        -- Geographic area
  pdf_path TEXT NOT NULL,
  char_count INTEGER,
  word_count INTEGER,
  total_regulatory_refs INTEGER,
  extraction_timestamp REAL,
  full_text TEXT NOT NULL
);
```

---

## 2. RELATIONSHIPS LAYER (Knowledge Graph)

### kg_relationships
**Purpose**: Semantic relationships between planning concepts
**Rows**: 2,734
```sql
CREATE TABLE kg_relationships (
  id INTEGER PRIMARY KEY,
  subject_text TEXT NOT NULL,    -- "R2 zone"
  predicate TEXT NOT NULL,       -- "requires"
  object_text TEXT NOT NULL,     -- "6m rear setback"
  subject_entity_id INTEGER,     -- Links to kg_entities
  object_entity_id INTEGER,
  relationship_context TEXT,
  document_id TEXT NOT NULL,
  page_number INTEGER,
  section_header TEXT,
  confidence_score REAL DEFAULT 1.0,
  original_ref_type TEXT NOT NULL,
  original_ref_id INTEGER,
  extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### kg_entities
**Purpose**: Named entities extracted from planning documents
**Rows**: 1,394
```sql
CREATE TABLE kg_entities (
  id INTEGER PRIMARY KEY,
  entity_type TEXT NOT NULL,     -- zone, setback, height, etc.
  entity_name TEXT NOT NULL,     -- "R2", "6m", "Inner West LEP"
  entity_description TEXT,
  document_id TEXT NOT NULL,
  page_number INTEGER,
  section_header TEXT,
  text_level INTEGER,
  original_ref_type TEXT NOT NULL,
  original_ref_id INTEGER,
  extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### kg_relationships_from_refs
**Purpose**: Relationships derived from regulatory references
**Rows**: 2,294
```sql
CREATE TABLE kg_relationships_from_refs (
  id INT PRIMARY KEY,
  document_id TEXT,
  relationship_type TEXT,
  relationship_context TEXT,
  page_number INT,
  section_header TEXT,
  relationship_summary TEXT,
  category TEXT
);
```

---

## 3. PATHWAYS LAYER (Development Controls & Standards)

### development_controls
**Purpose**: Structured development controls extracted from provisions
**Rows**: 4,526
```sql
CREATE TABLE development_controls (
  id INTEGER PRIMARY KEY,
  provision_id INTEGER NOT NULL,  -- Links to regulatory_provisions
  control_type TEXT NOT NULL,     -- setback, height, FSR
  control_subtype TEXT,           -- rear, side, front
  value_numeric REAL,             -- 6.0
  value_text TEXT,                -- "6m minimum"
  unit TEXT,                      -- m, %, storeys
  zone_applicable TEXT,           -- R2, general
  conditions TEXT,                -- Special conditions
  confidence_score REAL DEFAULT 1.0,
  extraction_method TEXT DEFAULT 'regex'
);
```

### quantitative_standards
**Purpose**: Numeric standards with confidence scoring
**Rows**: 829
```sql
CREATE TABLE quantitative_standards (
  id INTEGER PRIMARY KEY,
  provision_id INTEGER NOT NULL,
  numeric_value REAL NOT NULL,    -- 6.0
  unit TEXT NOT NULL,             -- m, %, storeys
  qualifier TEXT NOT NULL,        -- minimum, maximum
  context TEXT NOT NULL,          -- setback, height
  confidence_score REAL NOT NULL,
  raw_text TEXT,                  -- Original extracted text
  manual_verified BOOLEAN DEFAULT FALSE,
  created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### development_pathways
**Purpose**: Development approval pathways by zone/type
**Rows**: 1
```sql
CREATE TABLE development_pathways (
  id INTEGER PRIMARY KEY,
  development_type TEXT NOT NULL,
  zone TEXT NOT NULL,
  qualification_criteria JSON NOT NULL,
  pathway_type TEXT NOT NULL,     -- complying, merit, prohibited
  confidence_score REAL NOT NULL,
  source_provision_ids TEXT,
  manual_verified BOOLEAN DEFAULT FALSE,
  created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. HIERARCHY LAYER (NSW Planning Authority)

### sepp_lep_overrides
**Purpose**: SEPP overrides of LEP provisions (highest authority)
**Rows**: 91
```sql
CREATE TABLE sepp_lep_overrides (
  id INTEGER PRIMARY KEY,
  sepp_provision_id INTEGER NOT NULL,
  lep_clause_reference TEXT NOT NULL,
  override_type TEXT NOT NULL,
  confidence_score REAL NOT NULL,
  extracted_text TEXT,
  manual_verified BOOLEAN DEFAULT FALSE,
  created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. CONTEXTUAL LAYER (Guidance & Visual)

### contextual_guidance_real
**Purpose**: Planning guidance and interpretive material
**Rows**: 6,655
```sql
CREATE TABLE contextual_guidance_real (
  id INT PRIMARY KEY,
  document_id TEXT,
  guidance_type TEXT,        -- objective, guideline, note
  guidance_title TEXT,
  guidance_text TEXT,
  page_number INT,
  section_header TEXT,
  text_level INT,
  category TEXT
);
```

### visual_elements_real
**Purpose**: Diagrams, charts, and visual planning aids
**Rows**: 3,017
```sql
CREATE TABLE visual_elements_real (
  id INT PRIMARY KEY,
  document_id TEXT,
  visual_type TEXT,          -- diagram, table, chart
  visual_description TEXT,
  page_number INT,
  section_header TEXT,
  visual_caption TEXT,
  category TEXT
);
```

---

## 6. REFERENCE LAYER (Cross-References)

### regulatory_refs_core
**Purpose**: Internal and external regulatory references
**Rows**: 762
```sql
CREATE TABLE regulatory_refs_core (
  id INT PRIMARY KEY,
  document_id TEXT,
  ref_type TEXT,             -- clause, schedule, external
  ref_number TEXT,           -- 4.1.2, Schedule 1
  ref_context TEXT,
  page_number INT,
  section_header TEXT,
  text_level INT
);
```

### clause_relationships
**Purpose**: Parent-child relationships between clauses
**Rows**: 0 (unpopulated)
```sql
CREATE TABLE clause_relationships (
  id INTEGER PRIMARY KEY,
  parent_provision_id INTEGER NOT NULL,
  child_provision_id INTEGER NOT NULL,
  relationship_type TEXT NOT NULL,
  confidence_score REAL DEFAULT 1.0,
  langextract_source BOOLEAN DEFAULT TRUE
);
```

---

## 7. PERFORMANCE LAYER (Caching & System)

### query_cache
**Purpose**: Query result caching for performance
**Rows**: 0 (runtime populated)
```sql
CREATE TABLE query_cache (
  id INTEGER PRIMARY KEY,
  query_text TEXT NOT NULL,
  query_hash TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  access_count INTEGER DEFAULT 1,
  last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### sqlite_sequence
**Purpose**: SQLite auto-increment sequence tracking
**Rows**: 9 (system table)

---

## 8. LEGACY TABLES (Empty/Deprecated)

The following tables exist but are unpopulated (0 rows):
- `contextual_guidance` - Superseded by `contextual_guidance_real`
- `kg_visual_clause_links` - Visual-clause linking
- `kg_visual_elements` - Superseded by `visual_elements_real`
- `regulatory_refs` - Superseded by `regulatory_refs_core`
- `visual_elements` - Contains 1,473 rows but superseded by `visual_elements_real`

---

## Database Statistics Summary

| Table Category | Tables | Total Rows |
|---|---|---|
| **Provisions** | 3 | 31,730 |
| **Relationships** | 3 | 6,422 |
| **Controls** | 3 | 5,356 |
| **Hierarchy** | 1 | 91 |
| **Contextual** | 2 | 9,672 |
| **References** | 2 | 762 |
| **Performance** | 2 | 9 |
| **Legacy** | 5 | 1,473 |
| **TOTAL** | **21** | **55,515** |

---

## Query Patterns

### Hierarchical Authority Query (SEPP > LEP > DCP)
```sql
-- 1. Check SEPP overrides first
SELECT * FROM sepp_lep_overrides WHERE...

-- 2. If none, check LEP controls  
SELECT * FROM development_controls dc
JOIN documents d ON dc.document_id = d.id
WHERE d.document_type = 'LEP' AND...

-- 3. Fallback to DCP guidance
SELECT * FROM development_controls dc  
JOIN documents d ON dc.document_id = d.id
WHERE d.document_type = 'DCP' AND...
```

### Knowledge Graph Traversal
```sql
SELECT kr.subject_text, kr.predicate, kr.object_text
FROM kg_relationships kr
WHERE kr.subject_text LIKE '%setback%'
ORDER BY kr.confidence_score DESC;
```

### Contextual Enhancement
```sql
SELECT cg.guidance_text, ve.visual_description
FROM contextual_guidance_real cg
LEFT JOIN visual_elements_real ve ON cg.document_id = ve.document_id
WHERE cg.guidance_type = 'objective';
```

This architecture enables sophisticated planning compliance queries while respecting NSW planning hierarchy and providing rich contextual information.