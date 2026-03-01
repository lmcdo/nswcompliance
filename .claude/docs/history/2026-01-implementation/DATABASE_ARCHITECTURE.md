# Database Architecture Reference

## Core Provisions Architecture

### regulatory_provisions (BASE TABLE)
- **Rows:** 42,067 (includes 85 non-canonical)
- **Storage:** 50 MB table + 36 MB indexes
- **Purpose:** Source of truth for all planning provisions
- **Key Columns:**
  - `id` (PK) - provision identifier
  - `document_id` - source document (e.g., `Marrickville_DCP_2011_9_29_South_Western_Marrickville`)
  - `provision_text` - full provision content
  - `zone`, `development_type` - applicability filters
  - `is_canonical` - boolean flag (true = authoritative, false = draft/superseded)
  - `provision_tsv` - full-text search vector
  - `pdf_page`, `pdf_page_image_url` - source document reference

### regulatory_provisions_canonical (VIEW)
- **Rows:** 41,982 (filters WHERE is_canonical = true)
- **Storage:** 0 bytes (view = stored query, not duplicate data)
- **Extra Columns:** `document_type`, `document_area`, `pdf_name`, `pdf_path` (joined from documents table)
- **Purpose:** Guaranteed canonical provisions with document metadata

### The 85 Non-Canonical Rows
- **Cost:** 0.2% overhead (negligible)
- **Content:** LEP/SEPP metadata, version notes, 2 referenced by `quantitative_standards`
- **Decision:** Keep (preserves audit trail, zero storage cost from view)

## Data Architecture Pattern

### Foreign Key Constraints (Database Integrity)
```sql
-- Must FK to base table (can't FK to views)
REFERENCES regulatory_provisions(id)
```

### Query Pattern (Data Quality)
```sql
-- Always JOIN via canonical view
JOIN regulatory_provisions_canonical rpc ON x.provision_id = rpc.id

-- Direct queries use canonical
SELECT * FROM regulatory_provisions_canonical WHERE ...
```

### Current Usage (INCONSISTENT - needs standardization)
- `/api/dcp/provisions` → uses `regulatory_provisions` (base)
- `/api/compliance/constraints` → uses `regulatory_provisions_canonical` (view)
- **Standard:** All user-facing APIs should use canonical

## Key Tables

### documents (399 rows)
- **PK:** `id` (text, e.g., document identifier)
- **Purpose:** Document metadata, version tracking
- **Key Columns:** `pdf_name`, `document_type`, `document_area`, `source_url`, `amendment_date`, `version_status`

### development_controls (960 rows)
- **FK:** `provision_id` → regulatory_provisions(id)
- **Purpose:** Structured extraction of quantitative controls (setbacks, heights, etc.)
- **Key Columns:** `control_type`, `value_numeric`, `unit`, `zone_applicable`, `confidence_score`
- **Query Pattern:** JOIN via canonical view

### sepp_structured_requirements (2 rows)
- **FK:** `source_provision_id` → regulatory_provisions(id)
- **Purpose:** Manually curated SEPP compliance requirements (complex JSONB structure)
- **Key Columns:** `sepp_name`, `requirement_data` (nested JSONB), `development_type_category`
- **Note:** High curation effort, only 2 SEPPs processed

### provision_applicability (6,078 rows)
- **FK:** `provision_id` → regulatory_provisions(id)
- **Purpose:** Zone/LGA applicability rules
- **Key Columns:** `applies_to_zone`, `applies_to_all_zones`, `applies_to_lga`, `applies_state_wide`

### quantitative_standards (281 rows)
- **FK:** `provision_id` → regulatory_provisions(id)
- **Purpose:** Extracted numeric requirements
- **Key Columns:** `numeric_value`, `unit`, `qualifier`, `context`, `confidence_score`
- **Note:** 2 rows reference non-canonical provisions (can't delete all 85 non-canonical)

### heritage_conservation_areas (2,039 rows)
- **Purpose:** Geographic heritage overlays with polygon boundaries
- **Key Columns:** `h_name`, `geometry_json`, `lga_name`, `significance`, `legislative_clause`
- **No FK:** Standalone spatial data

## Document ID Patterns

### DCP (Development Control Plans)
- Base: `{LGA}_DCP_{Year}_Part_2_` (general controls)
- Dev-specific: `{LGA}_DCP_{Year}_Part_4.{X}` (e.g., 4.1 = low density)
- Precincts: `{LGA}_DCP_{Year}_9_{PrecinctNumber}_{PrecinctName}` (383 provisions, 15 precincts)

### SEPPs (State Environmental Planning Policies)
- Pattern: `State_Environmental_Planning_Policy_({Name})_{Year}`
- Example: `SEPP_(Sustainable_Buildings)_2022`

### LEPs (Local Environmental Plans)
- Pattern: `{LGA}_Local_Environmental_Plan_{Year}`
- Example: `Inner_West_Local_Environmental_Plan_2022`

## Precinct Provisions

### Current State
- **Location:** regulatory_provisions table (383 rows)
- **Pattern:** `document_id ~ '9_[0-9]+'`
- **All canonical:** is_canonical = true (100%)
- **Current API:** Not returned by DCP provisions API (no precinct matching in query pattern)

### Precinct Architecture Decision
**Don't copy SEPP pattern** (manual JSONB curation) because:
- SEPPs: 2 rows, complex pass/fail logic, manually curated
- Precincts: 383 rows, mostly qualitative guidance, user needs full text
- 83% of precinct content is qualitative (doesn't fit structured extraction)

**Proposed:** Simple table + canonical pattern
```sql
CREATE TABLE dcp_precinct_provisions (
    id SERIAL PRIMARY KEY,
    precinct_id TEXT NOT NULL,              -- '9_29'
    precinct_name TEXT NOT NULL,            -- 'South Western Marrickville'
    lga TEXT NOT NULL,
    provision_text TEXT NOT NULL,
    parent_provision_id INTEGER REFERENCES regulatory_provisions(id)
);

-- Query pattern
SELECT * FROM dcp_precinct_provisions pp
JOIN regulatory_provisions_canonical rpc ON pp.parent_provision_id = rpc.id;
```

## Best Practices

### 1. Always Use Canonical View
```sql
-- ✓ CORRECT
SELECT * FROM regulatory_provisions_canonical WHERE ...

-- ✗ WRONG (risk of duplicates)
SELECT * FROM regulatory_provisions WHERE ...
```

### 2. FK Pattern
```sql
-- FK constraint to base table
provision_id INTEGER REFERENCES regulatory_provisions(id)

-- Query JOIN via canonical
JOIN regulatory_provisions_canonical rpc ON x.provision_id = rpc.id
```

### 3. Benefits
- **Integrity:** One authoritative version per provision
- **Maintainability:** Clear, consistent pattern
- **Reliability:** No duplicate provisions to users
- **Simplicity:** One rule for developers: "always canonical"

## Storage Costs

| Table/View | Rows | Storage | Notes |
|------------|------|---------|-------|
| regulatory_provisions | 42,067 | 85 MB | Base table (50 MB + 36 MB indexes) |
| regulatory_provisions_canonical | 41,982 | 0 bytes | VIEW (no data duplication) |
| development_controls | 960 | ~1 MB | Structured extractions |
| provision_applicability | 6,078 | ~2 MB | Applicability rules |
| documents | 399 | <1 MB | Document metadata |

**Non-canonical overhead:** 85 rows = 0.2% (negligible)

## API Query Patterns (Current)

| API Route | Table Used | Status |
|-----------|------------|--------|
| `/api/dcp/provisions` | regulatory_provisions | ⚠️ Should use canonical |
| `/api/compliance/constraints` | regulatory_provisions_canonical | ✓ Correct |
| `/api/browse/*` | regulatory_provisions | ⚠️ Should use canonical |
| development_controls JOINs | regulatory_provisions_canonical | ✓ Correct |

**Migration needed:** Standardize all APIs to use canonical view
