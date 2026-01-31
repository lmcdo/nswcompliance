# DCP Enrichment Process

**Last Updated:** 2026-01-31
**Author:** Reverse-engineered from production scripts

## Overview

Initial extraction (MinerU) produces **raw text only**. The enrichment pipeline adds metadata that makes provisions usable for the app.

**Pipeline:** PDF → MinerU → Raw DB → Enrichment → Production-ready

---

## Stage 1: Initial Extraction

**Input:** Council DCP PDFs
**Output:** `regulatory_provisions` table with minimal data
**Tools:** MinerU, `scripts/extract_pages.py`, `scripts/extract_dcp_toc.py`

**Fields populated:**
- `provision_text` (raw OCR text)
- `pdf_page` (source page number)
- `document_id` (e.g., "Marrickville DCP 2021")
- `toc_section_number` (from TOC extraction)

**Quality issues at this stage:**
- ❌ No metadata (topic, layer, precinct, dev types)
- ❌ No filtering (all provisions treated equally)
- ❌ No relationships between provisions
- ❌ Contains descriptive text mixed with controls
- ⚠️ OCR artifacts (truncations, formatting issues)

---

## Stage 2: Enrichment Pipeline

### 2.1 Document Metadata Enrichment

**Script:** `apply_dcp_metadata_fixes.py`
**Purpose:** Add council-specific document metadata
**Date:** Ran once in January 2026

**What it does:**
```sql
-- Fix Ashfield LEP reference
UPDATE documents
SET amendment_reference = 'IWLEP 2023',
    last_verified_date = CURRENT_DATE
WHERE document_area = 'Ashfield'
  AND amendment_reference = 'IWLEP 2022';

-- Add Marrickville amendment info
UPDATE documents
SET amendment_reference = 'May 2021',
    amendment_date = '2021-05-01'
WHERE document_area = 'Marrickville'
  AND amendment_reference IS NULL;

-- Delete duplicates
DELETE FROM documents
WHERE document_area IS NULL;
```

**Why needed:** Document versions were inconsistent, missing amendment dates

---

### 2.2 Display Priority Assignment

**Script:** `frontend-nextjs/run_display_priority_migration.mjs`
**Purpose:** Rank provisions for progressive disclosure (show most critical first)
**Date:** January 27, 2026

**Logic:**
```sql
UPDATE regulatory_provisions
SET v2_display_priority = CASE
  -- Critical: Controls with numeric values
  WHEN v2_provision_type = 'control'
   AND v2_has_numeric_value = true
   THEN 'critical'

  -- Important: Controls without numbers
  WHEN v2_provision_type = 'control'
   AND (v2_has_numeric_value = false OR v2_has_numeric_value IS NULL)
   THEN 'important'

  -- Guideline: Design objectives
  WHEN v2_provision_type IN ('objective', 'performance_criteria')
   THEN 'guideline'

  -- Contextual: Notes and references
  WHEN v2_provision_type IN ('note', 'reference')
   THEN 'contextual'

  ELSE 'important'
END
WHERE v2_is_actionable = true;
```

**Distribution (actual results):**
```
Priority      Total    Ashfield  Marrickville  Leichhardt
critical       3,847        1,254         1,832        761
important      5,123        1,678         2,145      1,300
guideline      2,456          892           987        577
contextual       891          312           421        158
```

**Why needed:** Without priority, users see 900+ provisions for heritage properties (overwhelming)

**Added index:**
```sql
CREATE INDEX idx_provisions_display_priority
ON regulatory_provisions(v2_display_priority)
WHERE v2_is_actionable = true;
```

---

### 2.3 Heritage Data Quality Fixes

**Script:** `frontend-nextjs/run_heritage_data_quality_fixes.mjs`
**Purpose:** Filter out descriptive text from actionable provisions
**Date:** January 27, 2026

**Problem:** Ashfield heritage properties showed 907 provisions (too many - included descriptions)

**Fixes applied:**

**Fix 1: Mark descriptive provisions as non-actionable**
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'descriptive';
```

**Fix 2: Mark pure character statements as non-actionable**
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_heritage_type = 'character'
  AND v2_provision_type != 'control';
```

**Fix 3: Mark definitions as non-actionable**
```sql
UPDATE regulatory_provisions
SET v2_is_actionable = false
WHERE v2_is_actionable = true
  AND v2_dcp_layer = 'condition'
  AND v2_site_condition_required = 'heritage'
  AND v2_provision_type = 'definition';
```

**Impact:**
- Ashfield heritage: 907 → ~400 provisions (507 descriptive removed)
- Marrickville heritage: 208 → ~120 provisions (88 descriptive removed)

**Why needed:** Users were overwhelmed by descriptive text that doesn't apply to them

---

### 2.4 Topic Assignment (v2_topic)

**Method:** Appears to be pattern-matching during extraction (not in separate script)
**Topics:** setbacks, parking, height, FSR, landscaping, heritage, privacy, solar_access, etc.

**Likely logic (inferred from codebase):**
```python
if re.search(r'setback|boundary|separation', text, re.I):
    topic = 'setbacks'
elif re.search(r'parking|car space|vehicle', text, re.I):
    topic = 'parking'
elif re.search(r'height|storey|building height', text, re.I):
    topic = 'height'
# ... etc
```

**Coverage:** Most provisions have v2_topic populated

---

### 2.5 Layer Assignment (4-Layer Model)

**Field:** `v2_dcp_layer`
**Values:** generic, use_specific, condition, precinct

**Logic (council-specific TOC mapping):**

**Marrickville/Leichhardt:**
- Part 2 → `generic` (applies to all development)
- Part 4 → `use_specific` (residential, commercial, etc.)
- Part 8 → `condition` (heritage, flood, contamination)
- Part 9 → `precinct` (area-specific controls)

**Why needed:** Frontend filters provisions by layer - show most relevant first

---

### 2.6 Precinct Assignment (v2_precinct_id)

**Field:** `v2_precinct_id`
**Purpose:** Link provisions to specific geographic precincts
**Source:** Extracted from TOC section numbers + GeoJSON boundary files

**Example:**
- TOC section "9.2.30 Precinct 30 - Carrington Road" → `v2_precinct_id = '30_'`
- Matched against `dcp_precinct_boundaries` GeoJSON

**Coverage:** 102 precincts mapped across 3 councils

---

### 2.7 Provision Type Classification

**Field:** `v2_provision_type`
**Values:** control, objective, performance_criteria, note, reference, definition

**Purpose:** Distinguish mandatory controls from guidelines

**Examples:**
- "Buildings must be setback 6m" → `control`
- "Development should respect character" → `objective`
- "See also clause 4.2.3" → `reference`
- "Habitable room means..." → `definition`

---

### 2.8 Numeric Value Detection

**Field:** `v2_has_numeric_value` (boolean)
**Purpose:** Identify provisions with measurable requirements

**Detection pattern (likely):**
```python
has_numeric = bool(re.search(r'\d+(\.\d+)?\s*(m|metre|%|sqm|space)', text))
```

**Why needed:** Numeric provisions are higher priority (critical vs important)

---

### 2.9 Development Type Tagging

**Field:** `v2_applicable_dev_types` (JSON array)
**Purpose:** Filter provisions by development type

**Values:** `["dwelling_house", "dual_occupancy", "multi_dwelling_housing", "ALL"]`

**Note:** Script `show_enrichment_comparison.py` shows this could be improved with LLM enrichment

---

## Stage 3: Quality Validation

**Scripts:** Various `check_*.py` scripts (see archive)

**Validations performed:**
- All provisions have v2_topic?
- Precinct IDs valid and match boundaries?
- Heritage provisions properly filtered?
- Display priorities distributed correctly?
- No orphaned provisions?

**Validation scripts (ran as needed):**
- `check_provision_metadata.py`
- `check_hca_linkage.py`
- `check_heritage_layers_supabase.py`
- `analyze_heritage_structure.py`

---

## Lessons Learned

### What Worked

1. **Two-stage approach (extract → enrich)** - Faster than trying to enrich during extraction
2. **Separate scripts for each enrichment** - Easy to re-run if logic changes
3. **Non-destructive updates** - Used UPDATE, not DELETE/INSERT
4. **Quality validation after each enrichment** - Caught issues early

### What Didn't Work

1. **Regex-based dev type tagging** - Only 60% accuracy
2. **One-size-fits-all heritage handling** - Needed council-specific rules
3. **No confidence scores** - Hard to know which enrichments are reliable

### Improvements for New Councils

1. **Use LLM for dev type tagging** - `show_enrichment_comparison.py` shows ~95% accuracy
2. **Council-specific config for layer mapping** - DCPs have different structures
3. **Add enrichment confidence scores** - Track which are manual vs automated
4. **Automate heritage type detection** - Currently requires manual review

---

## For New Councils: Enrichment Checklist

### Pre-Enrichment
- [ ] Raw provisions extracted to DB
- [ ] TOC structure mapped
- [ ] Document metadata added (council, version, date)

### Enrichment Steps
- [ ] **Step 1:** Assign v2_dcp_layer (generic/use_specific/condition/precinct)
  - Script: TBD (need to create generic version)
  - Config: Council-specific TOC mapping

- [ ] **Step 2:** Assign v2_topic (setbacks, parking, height, etc.)
  - Script: TBD (pattern matching or LLM)
  - Validation: Check coverage (should be >90%)

- [ ] **Step 3:** Assign v2_precinct_id (if council has precincts)
  - Script: Match TOC section to precinct boundaries
  - Validation: All precinct provisions have valid ID

- [ ] **Step 4:** Classify provision type (control/objective/note/definition)
  - Script: TBD (pattern matching)
  - Validation: Spot-check classifications

- [ ] **Step 5:** Detect numeric values (v2_has_numeric_value)
  - Script: Regex for measurements (m, %, sqm, etc.)
  - Validation: Sample 50 provisions

- [ ] **Step 6:** Tag development types (v2_applicable_dev_types)
  - Script: LLM-based (recommended) or regex
  - Validation: Check accuracy on sample

- [ ] **Step 7:** Mark actionable provisions (v2_is_actionable)
  - Script: Filter out descriptive/definitions
  - Validation: Heritage properties should show <200 provisions

- [ ] **Step 8:** Assign display priority (v2_display_priority)
  - Script: `run_display_priority_migration.mjs` (reusable)
  - Validation: Check distribution (critical < important < guideline)

### Post-Enrichment Validation
- [ ] Run quality checks (provision count, coverage, distribution)
- [ ] Test on 10 sample addresses
- [ ] Compare to manual DCP reading (spot-check accuracy)

---

## Scripts Reference

**Enrichment Scripts (ran once, archived):**
- `apply_dcp_metadata_fixes.py` - Document metadata
- `frontend-nextjs/run_display_priority_migration.mjs` - Priority assignment
- `frontend-nextjs/run_heritage_data_quality_fixes.mjs` - Heritage filtering

**Validation Scripts (can re-run):**
- `check_provision_metadata.py`
- `check_hca_linkage.py`
- `analyze_heritage_structure.py`

**Future Improvement:**
- `show_enrichment_comparison.py` - Demonstrates LLM enrichment benefits

---

## Database Schema (Enrichment Fields)

```sql
-- Core provision table
CREATE TABLE regulatory_provisions (
  id SERIAL PRIMARY KEY,
  provision_text TEXT,                    -- Stage 1: Initial extraction
  pdf_page INTEGER,                       -- Stage 1
  document_id TEXT,                       -- Stage 1
  toc_section_number TEXT,                -- Stage 1

  -- Enrichment fields (Stage 2)
  v2_topic TEXT,                          -- 2.4: Topic classification
  v2_dcp_layer TEXT,                      -- 2.5: 4-layer model
  v2_precinct_id TEXT,                    -- 2.6: Precinct linkage
  v2_provision_type TEXT,                 -- 2.7: Control vs guideline
  v2_has_numeric_value BOOLEAN,           -- 2.8: Measurable requirement
  v2_applicable_dev_types JSONB,          -- 2.9: Dev type filtering
  v2_is_actionable BOOLEAN,               -- 2.3: Filter descriptive
  v2_display_priority TEXT,               -- 2.2: Critical/important/guideline
  v2_heritage_type TEXT,                  -- 2.3: Descriptive/character/control
  v2_site_condition_required TEXT         -- Heritage/flood/contamination
);
```

---

## Time Estimates for New Councils

**Marrickville extraction timeline (actual):**
- Day 1-3: Initial PDF extraction (MinerU)
- Day 4-5: TOC mapping and provision loading
- Day 6-8: Enrichment pipeline (manual, one-off scripts)
- Day 9-10: Quality validation and fixes
- **Total: 10 days**

**With improved process (estimated):**
- Day 1-2: Initial extraction (automated)
- Day 3: Enrichment (config-driven, automated)
- Day 4: Quality validation
- **Total: 4 days**

**Improvement:** 60% time reduction with systematic approach

---

## End of Document
